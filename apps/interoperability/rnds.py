"""Envio de Resultado de Exame Laboratorial (REL v2.0) à RNDS.

Fluxo: `queue_released_results()` cria um `RndsSubmission` por resultado liberado de exame
codificado; `send_pending()` monta o Bundle e envia. Faltou dado? O envio fica BLOCKED com
motivo técnico; nada é inferido. Ver docs/rnds.md e ADR 0009.
"""

import json
import unicodedata
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.admin.hr.models import Employee
from apps.clinical.lis.models import LabResult, RndsResultKind
from apps.clinical.pep.validators import normalize_cpf, validate_cns

from .models import RndsSubmission

# Base do guia FHIR v2.0 (rnds-fhir.saude.gov.br). O guia antigo usa
# http://www.saude.gov.br/fhir/r4; confirmar na homologação qual a RNDS aceita.
FHIR_BASE = "https://rnds-fhir.saude.gov.br"
TOKEN_CACHE_KEY = "rnds:access-token"
TOKEN_TTL_SECONDS = 25 * 60  # token vale 30 min; renova antes
TIMEOUT_SECONDS = (5, 30)
MAX_ATTEMPTS = 10
STALE_SENDING = timedelta(minutes=15)
QUALITATIVE_CODES = {"detectavel": "1", "nao detectavel": "2", "inconclusivo": "3"}


class RndsBlocked(Exception):
    """Faltam fatos para montar o documento; não é erro de rede."""


class RndsError(Exception):
    """Falha de comunicação ou recusa da RNDS; o envio pode ser repetido."""


def _fold(text):
    text = unicodedata.normalize("NFKD", text or "")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).lower().split())


def _moment(value):
    return timezone.localtime(value).isoformat(timespec="seconds")


def _structure(name, value):
    return {"system": f"{FHIR_BASE}/StructureDefinition/{name}", "value": value}


def _coding(code_system, code):
    return {"coding": [{"system": f"{FHIR_BASE}/CodeSystem/{code_system}", "code": code}]}


def _valid_cns(value):
    cns = normalize_cpf(value)
    try:
        validate_cns(cns)
    except ValidationError:
        return ""
    return cns


def professional_cns(user):
    cns = Employee.objects.filter(user=user).values_list("cns", flat=True).first()
    return _valid_cns(cns or "")


def _value(test, result):
    if test.rnds_result_kind == RndsResultKind.QUALITATIVE:
        code = QUALITATIVE_CODES.get(_fold(result.value))
        if not code:
            raise RndsBlocked(
                "Resultado qualitativo fora de Detectável/Não detectável/Inconclusivo."
            )
        return {"valueCodeableConcept": _coding("BRResultadoQualitativoExame", code)}
    try:
        number = Decimal(result.value.strip().replace(",", "."))
    except InvalidOperation:
        raise RndsBlocked("Resultado quantitativo não numérico.") from None
    quantity = {"value": float(number)}
    if result.unit:
        quantity["unit"] = result.unit
    return {"valueQuantity": quantity}


def build_bundle(result, *, document_key, replaces_rnds_id=None):
    """Monta o REL v2.0 a partir de um resultado liberado, ou levanta RndsBlocked."""
    order = result.specimen.service_request
    test, patient = order.lab_test, order.encounter.patient
    if not test.sends_to_rnds:
        raise RndsBlocked("Exame sem codificação RNDS completa no catálogo.")
    if result.status != LabResult.Status.RELEASED:
        raise RndsBlocked("Resultado ainda não liberado.")
    patient_cns = _valid_cns(patient.cns)
    if not patient_cns:
        raise RndsBlocked("Paciente sem CNS válido (a RNDS identifica o indivíduo pelo CNS).")
    performer_cns = professional_cns(result.released_by)
    if not performer_cns:
        raise RndsBlocked("Profissional que liberou o resultado sem CNS no cadastro funcional.")

    composition_ref, observation_ref, specimen_ref = (f"urn:uuid:{uuid.uuid4()}" for _ in range(3))
    subject = {"identifier": _structure("BRIndividuo-1.0", patient_cns)}
    issued = _moment(result.released_at)

    composition = {
        "resourceType": "Composition",
        "meta": {"profile": [f"{FHIR_BASE}/StructureDefinition/BRResultadoExameLaboratorial-2.0"]},
        "status": "final",
        "type": _coding("BRTipoDocumento", "REL"),
        "subject": subject,
        "date": issued,
        "author": [
            {"identifier": _structure("BREstabelecimentoSaude-1.0", settings.ESTABLISHMENT_CNES)}
        ],
        "title": "Resultado de Exame Laboratorial",
        "section": [{"entry": [{"reference": observation_ref}]}],
    }
    if replaces_rnds_id:
        composition["relatesTo"] = [
            {
                "code": "replaces",
                "targetReference": {"reference": f"Composition/{replaces_rnds_id}"},
            }
        ]

    observation = {
        "resourceType": "Observation",
        "meta": {
            "profile": [f"{FHIR_BASE}/StructureDefinition/BRDiagnosticoLaboratorioClinico-2.0"]
        },
        "status": "final",
        "category": [_coding("BRSubgrupoTabelaSUS", test.sus_subgroup)],
        "code": _coding(f"BRNomeExame{test.rnds_exam_system}", test.rnds_exam_code),
        "subject": subject,
        "effectiveDateTime": _moment(result.specimen.collected_at),
        "issued": issued,
        "performer": [
            {"identifier": _structure("BRPessoaJuridicaProfissionalLiberal-1.0", performer_cns)}
        ],
        **_value(test, result),
        "specimen": {"reference": specimen_ref},
    }
    if result.method:
        observation["method"] = {"text": result.method}
    if result.reference_range:
        observation["referenceRange"] = [{"text": result.reference_range}]

    specimen = {
        "resourceType": "Specimen",
        "meta": {"profile": [f"{FHIR_BASE}/StructureDefinition/BRAmostraBiologica-1.0"]},
        "type": _coding("BRTipoAmostraGAL", test.rnds_specimen_code),
    }

    return {
        "resourceType": "Bundle",
        "type": "document",
        "timestamp": _moment(timezone.now()),
        "identifier": {
            "system": f"{FHIR_BASE}/NamingSystem/BRRNDS-{settings.RNDS_REQUESTER_ID}",
            "value": str(document_key),
        },
        "entry": [
            {"fullUrl": composition_ref, "resource": composition},
            {"fullUrl": observation_ref, "resource": observation},
            {"fullUrl": specimen_ref, "resource": specimen},
        ],
    }


def _hosts():
    if settings.RNDS_ENVIRONMENT == "prod":
        uf = settings.ESTABLISHMENT_UF.lower()
        return "ehr-auth.saude.gov.br", f"{uf}-ehr-services.saude.gov.br"
    return "ehr-auth-hmg.saude.gov.br", "ehr-services.hmg.saude.gov.br"


def access_token():
    """Token de 30 min obtido com o certificado (mTLS); nunca vai para log."""
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token
    auth_host, _ = _hosts()
    try:
        response = requests.get(
            f"https://{auth_host}/api/token",
            cert=(settings.RNDS_CERT_FILE, settings.RNDS_KEY_FILE),
            timeout=TIMEOUT_SECONDS,
        )
    except (requests.RequestException, OSError) as exc:
        raise RndsError(f"Falha ao obter token ({type(exc).__name__}).") from None
    if response.status_code != 200:
        raise RndsError(f"Token recusado (HTTP {response.status_code}).")
    try:
        token = response.json()["access_token"]
    except ValueError, KeyError:
        raise RndsError("Resposta de token sem access_token.") from None
    cache.set(TOKEN_CACHE_KEY, token, TOKEN_TTL_SECONDS)
    return token


def _issue_codes(response):
    """Só os códigos do OperationOutcome; 'diagnostics' pode ecoar dados do paciente."""
    try:
        issues = response.json().get("issue", [])
    except ValueError, AttributeError:
        return ""
    codes = sorted({str(issue.get("code", "")) for issue in issues if isinstance(issue, dict)})
    return f": {', '.join(code for code in codes if code)}" if codes else ""


def post_bundle(bundle, performer_cns):
    _, ehr_host = _hosts()
    try:
        response = requests.post(
            f"https://{ehr_host}/api/fhir/r4/Bundle",
            data=json.dumps(bundle, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/fhir+json",
                "X-Authorization-Server": f"Bearer {access_token()}",
                "Authorization": performer_cns,
            },
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RndsError(f"Falha de rede no envio ({type(exc).__name__}).") from None
    if response.status_code == 401:
        cache.delete(TOKEN_CACHE_KEY)
    if response.status_code != 201:
        raise RndsError(
            f"RNDS recusou o envio (HTTP {response.status_code}{_issue_codes(response)})."
        )
    location = response.headers.get("location") or response.headers.get("content-location") or ""
    rnds_id = location.rstrip("/").rsplit("/", 1)[-1]
    if not rnds_id:
        raise RndsError("RNDS aceitou sem informar o código do documento (Location).")
    return rnds_id


def _results_to_queue():
    since = date.fromisoformat(settings.RNDS_SEND_SINCE)
    return (
        LabResult.objects.filter(
            status=LabResult.Status.RELEASED,
            released_at__date__gte=since,
            rnds_submission__isnull=True,
        )
        .exclude(specimen__service_request__lab_test__rnds_exam_code="")
        .exclude(superseded_by__status=LabResult.Status.RELEASED)
    )


def _sent_predecessor(result):
    """Versão anterior já enviada: o novo resultado a substitui na RNDS."""
    previous = result.supersedes
    while previous is not None:
        submission = RndsSubmission.objects.filter(
            lab_result=previous, status=RndsSubmission.Status.SENT
        ).first()
        if submission:
            return submission
        previous = previous.supersedes
    return None


def queue_released_results():
    created = 0
    for result in _results_to_queue().select_related("supersedes"):
        predecessor = _sent_predecessor(result)
        _, was_created = RndsSubmission.objects.get_or_create(
            lab_result=result,
            defaults={
                "replaces": predecessor,
                "document_key": predecessor.document_key if predecessor else uuid.uuid4(),
                "environment": settings.RNDS_ENVIRONMENT,
            },
        )
        created += was_created
    return created


def _claim(submission):
    """Marca como SENDING só se ninguém pegou antes (duas execuções não enviam em dobro)."""
    return bool(
        RndsSubmission.objects.filter(pk=submission.pk, status=submission.status).update(
            status=RndsSubmission.Status.SENDING, updated_at=timezone.now()
        )
    )


def _finish(submission, status, detail="", **extra):
    RndsSubmission.objects.filter(pk=submission.pk).update(
        status=status, detail=detail[:255], updated_at=timezone.now(), **extra
    )


def send_submission(submission):
    if not _claim(submission):
        return None
    result = submission.lab_result
    if LabResult.objects.filter(supersedes=result, status=LabResult.Status.RELEASED).exists():
        _finish(submission, RndsSubmission.Status.BLOCKED, "Resultado retificado antes do envio.")
        return RndsSubmission.Status.BLOCKED
    try:
        bundle = build_bundle(
            result,
            document_key=submission.document_key,
            replaces_rnds_id=submission.replaces.rnds_id if submission.replaces else None,
        )
    except RndsBlocked as exc:
        _finish(submission, RndsSubmission.Status.BLOCKED, str(exc))
        return RndsSubmission.Status.BLOCKED
    attempts = submission.attempts + 1
    try:
        rnds_id = post_bundle(bundle, professional_cns(result.released_by))
    except RndsError as exc:
        _finish(submission, RndsSubmission.Status.FAILED, str(exc), attempts=attempts)
        return RndsSubmission.Status.FAILED
    _finish(
        submission,
        RndsSubmission.Status.SENT,
        rnds_id=rnds_id,
        attempts=attempts,
        sent_at=timezone.now(),
    )
    return RndsSubmission.Status.SENT


def send_pending(limit=100):
    """Envia pendentes, reavalia bloqueados e repete falhas até MAX_ATTEMPTS."""
    RndsSubmission.objects.filter(
        status=RndsSubmission.Status.SENDING, updated_at__lt=timezone.now() - STALE_SENDING
    ).update(status=RndsSubmission.Status.FAILED, detail="Envio interrompido; repetindo.")
    candidates = (
        RndsSubmission.objects.filter(
            Q(status__in=[RndsSubmission.Status.PENDING, RndsSubmission.Status.BLOCKED])
            | Q(status=RndsSubmission.Status.FAILED, attempts__lt=MAX_ATTEMPTS)
        )
        .select_related(
            "replaces",
            "lab_result__released_by",
            "lab_result__specimen__service_request__lab_test",
            "lab_result__specimen__service_request__encounter__patient",
        )
        # Reavaliação atualiza updated_at: bloqueados vão para o fim e não travam a fila.
        .order_by("updated_at")[:limit]
    )
    outcome = {}
    for submission in candidates:
        status = send_submission(submission)
        if status:
            outcome[status] = outcome.get(status, 0) + 1
    return outcome
