import random
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.clinical.adt.lifecycle import discharge_patient
from apps.clinical.adt.models import Bed, Discharge, Location
from apps.clinical.adt.services import admit_patient
from apps.clinical.pep.models import Encounter, Patient

NAMES = [
    "Maria Demo da Silva",
    "José Demo Santos",
    "Ana Demo Oliveira",
    "João Demo Souza",
    "Francisca Demo Lima",
    "Antônio Demo Pereira",
    "Luzia Demo Ferreira",
    "Paulo Demo Costa",
]
MUNICIPALITY = "2611606"  # Recife/PE
ADMITTED = 6
DISCHARGED = 2


def fake_cns(rng):
    """CNS provisório (inicia em 7) que passa em validate_cns."""
    while True:
        base = "7" + "".join(rng.choices("0123456789", k=13))
        check = -sum(int(d) * w for d, w in zip(base, range(15, 1, -1), strict=True)) % 11
        if check < 10:
            return base + str(check)


def _key(label):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"aegismed-demo-{label}")


class Command(BaseCommand):
    help = "Cria dados sintéticos de demonstração (somente com DEBUG=True)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, seed, **options):
        if not settings.DEBUG:
            raise CommandError("Recusado: dados demonstrativos só com DEBUG=True.")
        actor = (
            get_user_model()
            .objects.filter(is_superuser=True, nivel_permissao="ADM")
            .order_by("pk")
            .first()
        )
        if actor is None:
            raise CommandError("Crie antes um superusuário com nível de permissão ADM.")

        rng = random.Random(seed)  # determinístico: rodar de novo não duplica
        ward, _ = Location.objects.get_or_create(
            code="DEMO-CM",
            defaults={"name": "Clínica Médica (demo)", "kind": Location.Kind.WARD},
        )
        beds = [
            Bed.objects.get_or_create(
                location=ward, code=f"{n:02}", defaults={"label": f"Leito {n:02}"}
            )[0]
            for n in range(1, 11)
        ]

        created = 0
        for index, name in enumerate(NAMES):
            cns = fake_cns(rng)
            birth_offset = rng.randint(0, 25000)
            sex = rng.choice([Patient.Sex.FEMALE, Patient.Sex.MALE])
            stay_days = rng.randint(2, 10)
            if Patient.objects.filter(
                identifier_type=Patient.IdentifierType.CNS, identifier=cns
            ).exists():
                continue

            patient = Patient(
                identifier_type=Patient.IdentifierType.CNS,
                identifier=cns,
                cns=cns,
                full_name=name,
                birth_date=date(1940, 1, 1) + timedelta(days=birth_offset),
                sex=sex,
                municipality_code=MUNICIPALITY,
                city="Recife",
                state="PE",
                created_by=actor,
            )
            patient.full_clean()  # garante que o CNS gerado passa no validador real
            patient.save()
            created += 1

            if index >= ADMITTED:
                continue
            admitted_at = timezone.now() - timedelta(days=stay_days)
            encounter = Encounter.objects.create(
                patient=patient,
                encounter_type=Encounter.Type.INPATIENT,
                started_at=admitted_at,
                responsible_professional=actor,
                created_by=actor,
            )
            admission = admit_patient(
                encounter_id=encounter.pk,
                bed_id=beds[index].pk,
                actor=actor,
                admitted_at=admitted_at,
                operation_key=_key(f"admission-{cns}"),
            )
            if index < DISCHARGED:
                discharge_patient(
                    admission_id=admission.pk,
                    disposition=Discharge.Disposition.HOME,
                    actor=actor,
                    operation_key=_key(f"discharge-{cns}"),
                    discharged_at=timezone.now() - timedelta(hours=1),
                )

        self.stdout.write(
            self.style.SUCCESS(f"Dados demonstrativos: {created} paciente(s) criado(s).")
        )
