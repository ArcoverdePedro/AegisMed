from auditlog.signals import accessed
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_GET, require_http_methods

from apps.clinical.pep.models import Encounter
from apps.clinical.pep.permissions import accessible_patients
from apps.clinical.prescription.models import MedicationDispenseItem, MedicationRequest

from .forms import MedicationAdministrationForm, VitalSignsRecordForm
from .models import VitalSignsRecord
from .permissions import (
    PERM_ADMINISTER_MEDICATION,
    PERM_RECORD_VITALS,
    PERM_VIEW,
    can_administer_dispense_item,
    can_record_vitals,
    has_nursing_permission,
)
from .services import (
    MedicationAdministrationIdempotencyConflictError,
    MedicationAdministrationStateError,
    administer_medication,
    record_vital_signs,
)


def _no_store(response):
    response["Cache-Control"] = "private, no-store, max-age=0"
    patch_vary_headers(response, ("Cookie", "HX-Request"))
    return response


def _audit_access(*instances):
    for instance in instances:
        if instance is not None:
            accessed.send(instance.__class__, instance=instance)


def _scoped_encounter_or_404(user, pk):
    return get_object_or_404(
        Encounter.objects.select_related("patient", "responsible_professional").filter(
            patient__in=accessible_patients(user)
        ),
        pk=pk,
    )


def _scoped_dispense_item_or_404(user, pk):
    return get_object_or_404(
        MedicationDispenseItem.objects.select_related(
            "dispense__medication_request__encounter__patient",
            "request_item__drug",
            "lot__stock_item",
        ).filter(dispense__medication_request__encounter__patient__in=accessible_patients(user)),
        pk=pk,
    )


@login_required
@require_GET
def nursing_worklist(request):
    if not has_nursing_permission(request.user, PERM_VIEW):
        raise PermissionDenied

    encounters = (
        Encounter.objects.select_related("patient", "responsible_professional")
        .filter(patient__in=accessible_patients(request.user))
        .order_by("-started_at")
        .distinct()
    )
    paginator = Paginator(encounters, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    rendered_encounters = list(page_obj.object_list)
    _audit_access(*rendered_encounters)
    return _no_store(
        render(
            request,
            "clinical/nursing/worklist.html",
            {"encounters": rendered_encounters, "page_obj": page_obj},
        )
    )


@login_required
@require_GET
def nursing_encounter(request, pk):
    if not has_nursing_permission(request.user, PERM_VIEW):
        raise PermissionDenied

    encounter = _scoped_encounter_or_404(request.user, pk)
    vital_signs = list(
        encounter.nursing_vital_signs.select_related("recorded_by", "replaces").all()[:50]
    )
    _audit_access(encounter, *vital_signs)
    return _no_store(
        render(
            request,
            "clinical/nursing/encounter.html",
            {
                "encounter": encounter,
                "vital_signs": vital_signs,
                "can_record_vitals": can_record_vitals(request.user, encounter),
                "can_administer_medications": (
                    encounter.status == Encounter.Status.OPEN
                    and has_nursing_permission(
                        request.user,
                        PERM_ADMINISTER_MEDICATION,
                    )
                ),
            },
        )
    )


@login_required
@require_http_methods(["GET", "POST"])
def vitals_create(request, encounter_id):
    if not has_nursing_permission(request.user, PERM_RECORD_VITALS):
        raise PermissionDenied

    encounter = _scoped_encounter_or_404(request.user, encounter_id)
    if not can_record_vitals(request.user, encounter):
        raise PermissionDenied

    form = VitalSignsRecordForm(
        request.POST or None,
        encounter=encounter,
    )
    if request.method == "POST" and form.is_valid():
        record_vital_signs(
            encounter=encounter,
            actor=request.user,
            data=form.cleaned_data,
        )
        messages.success(request, "Sinais vitais registrados com sucesso.")
        return _no_store(redirect("nursing:encounter", pk=encounter.pk))

    _audit_access(encounter)
    return _no_store(
        render(
            request,
            "clinical/nursing/vitals_form.html",
            {
                "form": form,
                "encounter": encounter,
            },
        )
    )


@login_required
@require_http_methods(["GET", "POST"])
def vitals_correct(request, record_id):
    if not has_nursing_permission(request.user, PERM_RECORD_VITALS):
        raise PermissionDenied

    original = get_object_or_404(
        VitalSignsRecord.objects.select_related(
            "encounter__patient",
            "encounter__responsible_professional",
            "recorded_by",
        ).filter(encounter__patient__in=accessible_patients(request.user)),
        pk=record_id,
    )
    encounter = original.encounter
    if not can_record_vitals(request.user, encounter):
        raise PermissionDenied

    initial = None
    if request.method == "GET":
        initial = {
            field_name: getattr(original, field_name)
            for field_name in VitalSignsRecordForm.Meta.fields
        }

    form = VitalSignsRecordForm(
        request.POST or None,
        encounter=encounter,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        record_vital_signs(
            encounter=encounter,
            actor=request.user,
            data=form.cleaned_data,
            replaces=original,
        )
        messages.success(request, "Correção de sinais vitais registrada com sucesso.")
        return _no_store(redirect("nursing:encounter", pk=encounter.pk))

    _audit_access(encounter, original)
    return _no_store(
        render(
            request,
            "clinical/nursing/vitals_form.html",
            {
                "form": form,
                "encounter": encounter,
                "is_correction": True,
                "original_record": original,
            },
        )
    )


@login_required
@require_GET
def medication_list(request, encounter_id):
    if not has_nursing_permission(request.user, PERM_ADMINISTER_MEDICATION):
        raise PermissionDenied

    encounter = _scoped_encounter_or_404(request.user, encounter_id)
    if encounter.status != Encounter.Status.OPEN:
        raise PermissionDenied

    dispense_items = list(
        MedicationDispenseItem.objects.select_related(
            "dispense__medication_request",
            "request_item__drug",
            "lot__stock_item",
        )
        .filter(
            dispense__medication_request__encounter=encounter,
            dispense__medication_request__status=MedicationRequest.Status.VALIDATED,
            request_item__medication_request=F("dispense__medication_request"),
            lot__stock_item__drug=F("request_item__drug"),
        )
        .order_by("-dispense__dispensed_at", "request_item__sequence", "created_at")
    )
    _audit_access(encounter, *dispense_items)
    return _no_store(
        render(
            request,
            "clinical/nursing/medications.html",
            {
                "encounter": encounter,
                "dispense_items": dispense_items,
            },
        )
    )


@login_required
@require_http_methods(["GET", "POST"])
def medication_administer(request, dispense_item_id):
    if not has_nursing_permission(request.user, PERM_ADMINISTER_MEDICATION):
        raise PermissionDenied

    dispense_item = _scoped_dispense_item_or_404(request.user, dispense_item_id)
    if not can_administer_dispense_item(request.user, dispense_item):
        raise PermissionDenied

    form = MedicationAdministrationForm(
        request.POST or None,
        dispense_item=dispense_item,
    )
    response_status = 200
    if request.method == "POST" and form.is_valid():
        try:
            administer_medication(
                dispense_item_id=dispense_item.pk,
                actor=request.user,
                data={
                    "administered_at": form.cleaned_data["administered_at"],
                    "administered_dose": form.cleaned_data["administered_dose"],
                    "administered_dose_unit": form.cleaned_data["administered_dose_unit"],
                },
                operation_key=form.cleaned_data["operation_key"],
            )
        except MedicationAdministrationIdempotencyConflictError:
            form.add_error(
                None,
                "Esta confirmação não corresponde à operação já registrada. Recarregue a tela.",
            )
            response_status = 409
        except MedicationAdministrationStateError:
            form.add_error(
                None,
                "O item dispensado não está mais disponível para esta confirmação.",
            )
            response_status = 409
        except PermissionDenied:
            raise
        except ValidationError:
            form.add_error(
                None,
                "Não foi possível confirmar a administração com os dados informados.",
            )
            response_status = 409
        else:
            messages.success(request, "Administração registrada com sucesso.")
            encounter_id = dispense_item.dispense.medication_request.encounter_id
            return _no_store(redirect("nursing:medication_list", encounter_id=encounter_id))

    encounter = dispense_item.dispense.medication_request.encounter
    _audit_access(encounter, dispense_item)
    return _no_store(
        render(
            request,
            "clinical/nursing/medication_administer.html",
            {
                "form": form,
                "dispense_item": dispense_item,
                "encounter": encounter,
            },
            status=response_status,
        )
    )
