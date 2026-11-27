import datetime as dt

from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone

from apps.clinical.pep.models import Encounter
from apps.clinical.pep.permissions import accessible_patients

from .models import Admission, Bed, BedOccupancy, Discharge
from .permissions import accessible_locations


def available_beds_for_user(user):
    active_occupancy = BedOccupancy.objects.filter(
        bed_id=OuterRef("pk"),
        ended_at__isnull=True,
    )
    return (
        Bed.objects.filter(
            active=True,
            operational_status=Bed.OperationalStatus.AVAILABLE,
            location__in=accessible_locations(user),
        )
        .annotate(has_active_occupancy=Exists(active_occupancy))
        .filter(has_active_occupancy=False)
        .select_related("location")
        .order_by("location__name", "code")
    )


def admissible_encounters_for_user(user):
    return (
        Encounter.objects.filter(
            patient__in=accessible_patients(user),
            encounter_type=Encounter.Type.INPATIENT,
            status=Encounter.Status.OPEN,
            adt_admission__isnull=True,
        )
        .select_related("patient")
        .order_by("-started_at")
    )


def admissions_for_user(user):
    patient_ids = accessible_patients(user).order_by().values("pk")
    queryset = Admission.objects.filter(encounter__patient_id__in=patient_ids)
    if not getattr(user, "is_admin", lambda: False)():
        queryset = queryset.filter(
            occupancies__bed__location__in=accessible_locations(user)
        )
    return queryset.select_related("encounter__patient", "admitted_by").distinct()


def active_admissions_for_user(user):
    active_occupancy = BedOccupancy.objects.filter(
        admission_id=OuterRef("pk"),
        ended_at__isnull=True,
        bed__location__in=accessible_locations(user),
    )
    return (
        Admission.objects.filter(
            encounter__patient__in=accessible_patients(user),
            encounter__status=Encounter.Status.OPEN,
            discharge__isnull=True,
        )
        .annotate(has_active_occupancy=Exists(active_occupancy))
        .filter(has_active_occupancy=True)
        .select_related("encounter__patient", "admitted_by")
        .order_by("-admitted_at")
    )


def bed_map_groups(user):
    active_occupancies = BedOccupancy.objects.filter(ended_at__isnull=True).select_related(
        "admission__encounter__patient"
    )
    beds = (
        Bed.objects.filter(active=True, location__in=accessible_locations(user))
        .select_related("location")
        .prefetch_related(
            Prefetch(
                "occupancies",
                queryset=active_occupancies,
                to_attr="active_occupancies",
            )
        )
        .order_by("location__name", "code")
    )

    visible_patient_ids = set(
        accessible_patients(user).order_by().values_list("pk", flat=True)
    )
    groups = {}
    for bed in beds:
        occupancy = bed.active_occupancies[0] if bed.active_occupancies else None
        status = "OCCUPIED" if occupancy else bed.operational_status
        patient = occupancy.admission.encounter.patient if occupancy else None
        show_phi = bool(patient and patient.pk in visible_patient_ids)
        row = {
            "bed": bed,
            "status": status,
            "occupancy": occupancy,
            "patient": patient if show_phi else None,
            "show_phi": show_phi,
        }
        groups.setdefault(bed.location, []).append(row)
    return list(groups.items())


def _pct(num, den):
    return round(100 * num / den, 2) if den else None


def _ratio(num, den):
    return round(num / den, 2) if den else None


def hospital_census(user, start, end):
    """Indicadores do censo hospitalar (Padronização da Nomenclatura do Censo Hospitalar, MS)."""
    locations = accessible_locations(user)
    tz = timezone.get_current_timezone()
    days = (end - start).days + 1
    period_start = dt.datetime.combine(start, dt.time.min, tz)
    # Censo à meia-noite: conta quem estava no leito ao fim de cada dia.
    census = [
        dt.datetime.combine(start + dt.timedelta(days=n + 1), dt.time.min, tz)
        for n in range(days)
    ]

    occupancies = (
        BedOccupancy.objects.filter(bed__location__in=locations, started_at__lt=census[-1])
        .filter(Q(ended_at__isnull=True) | Q(ended_at__gt=census[0]))
        .values_list("started_at", "ended_at")
    )
    patient_days = sum(
        1
        for started, ended in occupancies
        for moment in census
        if started <= moment and (ended is None or ended > moment)
    )

    discharges = list(
        Discharge.objects.filter(
            final_occupancy__bed__location__in=locations,
            discharged_at__gte=period_start,
            discharged_at__lt=census[-1],
        ).values_list("disposition", "discharged_at", "admission__admitted_at")
    )
    # MS: quem interna e sai no mesmo dia conta 1 paciente-dia.
    patient_days += sum(
        1
        for _, out, admitted in discharges
        if timezone.localdate(out) == timezone.localdate(admitted)
    )
    death_stays = [
        out - admitted
        for disposition, out, admitted in discharges
        if disposition == Discharge.Disposition.DEATH
    ]
    # Saídas = altas + transferências externas + óbitos; transferência interna não é saída.
    exits = len(discharges)

    # shortcut: usa a situação atual dos leitos; reconstruir via BedStatusChange se o hospital pedir histórico.
    beds = (
        Bed.objects.filter(location__in=locations, active=True)
        .exclude(
            operational_status__in=[
                Bed.OperationalStatus.BLOCKED,
                Bed.OperationalStatus.OUT_OF_SERVICE,
            ]
        )
        .count()
    )
    bed_days = beds * days

    return {
        "Período": f"{start:%d/%m/%Y} a {end:%d/%m/%Y}",
        "Leitos operacionais": beds,
        "Leito-dia": bed_days,
        "Paciente-dia": patient_days,
        "Saídas": exits,
        "Óbitos": len(death_stays),
        "Taxa de ocupação (%)": _pct(patient_days, bed_days),
        "Média de permanência (dias)": _ratio(patient_days, exits),
        "Giro de rotatividade": _ratio(exits, beds),
        "Intervalo de substituição (dias)": _ratio(bed_days - patient_days, exits),
        "Taxa de mortalidade hospitalar (%)": _pct(len(death_stays), exits),
        "Taxa de mortalidade institucional (%)": _pct(
            sum(1 for stay in death_stays if stay >= dt.timedelta(hours=24)), exits
        ),
    }
