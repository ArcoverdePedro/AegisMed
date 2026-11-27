import random
import re
import uuid
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.admin.hr.models import Employee
from apps.clinical.lis.models import LabResult, LabTest
from apps.clinical.lis.services import advance_result, enter_result
from apps.clinical.lis.tests import test_specimen_lifecycle, test_workflow
from apps.clinical.pep.management.commands.seed_demo import fake_cns
from apps.clinical.pep.tests.test_views import TEST_STORAGES

from .. import rnds
from ..models import RndsSubmission

RNDS_SETTINGS = {
    "RNDS_ENABLED": True,
    "RNDS_ENVIRONMENT": "hmg",
    "RNDS_REQUESTER_ID": "REQ1",
    "RNDS_CERT_FILE": "/run/secrets/rnds.crt",
    "RNDS_KEY_FILE": "/run/secrets/rnds.key",
    "RNDS_SEND_SINCE": "2000-01-01",
    "ESTABLISHMENT_CNES": "1234567",
    "ESTABLISHMENT_UF": "PE",
}
FHIR = rnds.FHIR_BASE


def _response(status, *, json_body=None, headers=None):
    response = mock.Mock(status_code=status, headers=headers or {})
    response.json.return_value = json_body or {}
    return response


@override_settings(STORAGES=TEST_STORAGES, SECURE_SSL_REDIRECT=False, **RNDS_SETTINGS)
class RndsTests(TestCase):
    setUpTestData = classmethod(test_workflow.LisTests.setUpTestData.__func__)
    order = test_workflow.LisTests.order
    collect = test_specimen_lifecycle.SpecimenLifecycleTests.collect
    receive = test_specimen_lifecycle.SpecimenLifecycleTests.receive

    def setUp(self):
        cache.clear()
        rng = random.Random(7)
        self.patient_cns, self.professional_cns = fake_cns(rng), fake_cns(rng)
        self.patient.cns = self.patient_cns
        self.patient.save()
        Employee.objects.create(
            user=self.user,
            department="Laboratório",
            job_title="Bioquímico",
            cns=self.professional_cns,
        )
        LabTest.objects.filter(pk=self.test.pk).update(
            rnds_exam_system="GAL",
            rnds_exam_code="COVID",
            rnds_specimen_code="SGHEM",
            sus_subgroup="0214",
            rnds_result_kind="QUALITATIVE",
        )
        self.test.refresh_from_db()

    def release(self, value="Não detectável", supersedes=None, code=None):
        if supersedes is None:
            code = code or f"RNDS-{uuid.uuid4().hex[:6]}"
            specimen = self.collect(self.order(), code)
            self.receive(code)
        else:
            specimen = supersedes.specimen
        result = enter_result(
            user=self.user,
            specimen_id=specimen.pk,
            operation_key=uuid.uuid4(),
            supersedes=supersedes,
            reason="Retificação" if supersedes else "",
            analyte="SARS-CoV-2",
            value=value,
            method="RT-PCR",
        )
        advance_result(user=self.user, result_id=result.pk)
        return advance_result(user=self.user, result_id=result.pk)

    def test_bundle_follows_rel_v2_without_condition(self):
        result = self.release()

        bundle = rnds.build_bundle(result, document_key="doc-1")

        composition, observation, specimen = (entry["resource"] for entry in bundle["entry"])
        self.assertEqual(
            [r["resourceType"] for r in (composition, observation, specimen)],
            ["Composition", "Observation", "Specimen"],
        )
        self.assertEqual(
            bundle["identifier"],
            {"system": f"{FHIR}/NamingSystem/BRRNDS-REQ1", "value": "doc-1"},
        )
        self.assertEqual(composition["type"]["coding"][0]["code"], "REL")
        self.assertEqual(
            composition["subject"]["identifier"],
            {"system": f"{FHIR}/StructureDefinition/BRIndividuo-1.0", "value": self.patient_cns},
        )
        self.assertEqual(composition["author"][0]["identifier"]["value"], "1234567")
        self.assertEqual(
            observation["code"]["coding"][0],
            {"system": f"{FHIR}/CodeSystem/BRNomeExameGAL", "code": "COVID"},
        )
        self.assertEqual(observation["category"][0]["coding"][0]["code"], "0214")
        self.assertEqual(observation["valueCodeableConcept"]["coding"][0]["code"], "2")
        self.assertEqual(observation["performer"][0]["identifier"]["value"], self.professional_cns)
        self.assertRegex(observation["effectiveDateTime"], r"[+-]\d\d:\d\d$")
        self.assertEqual(specimen["type"]["coding"][0]["code"], "SGHEM")
        self.assertNotIn("relatesTo", composition)

    def test_missing_facts_block_without_guessing(self):
        result = self.release(value="Positivo")
        with self.assertRaisesRegex(rnds.RndsBlocked, "qualitativo"):
            rnds.build_bundle(result, document_key="x")

        result = self.release()
        Employee.objects.filter(user=self.user).update(cns="")
        with self.assertRaisesRegex(rnds.RndsBlocked, "Profissional"):
            rnds.build_bundle(result, document_key="x")

        self.patient.cns = ""
        self.patient.save()
        result = LabResult.objects.get(pk=result.pk)
        with self.assertRaisesRegex(rnds.RndsBlocked, "Paciente sem CNS"):
            rnds.build_bundle(result, document_key="x")

    def test_uncoded_exam_and_old_results_are_not_queued(self):
        self.release()
        LabTest.objects.filter(pk=self.test.pk).update(rnds_exam_code="")
        self.assertEqual(rnds.queue_released_results(), 0)

        LabTest.objects.filter(pk=self.test.pk).update(rnds_exam_code="COVID")
        with self.settings(RNDS_SEND_SINCE="2999-01-01"):
            self.assertEqual(rnds.queue_released_results(), 0)
        self.assertEqual(rnds.queue_released_results(), 1)
        self.assertEqual(rnds.queue_released_results(), 0)

    @mock.patch("apps.interoperability.rnds.requests.post")
    @mock.patch("apps.interoperability.rnds.requests.get")
    def test_send_and_rectification_replace_same_document(self, get, post):
        get.return_value = _response(200, json_body={"access_token": "tok"})
        post.return_value = _response(
            201, headers={"location": "https://ehr/api/fhir/r4/Composition/abc123"}
        )
        first = self.release()
        rnds.queue_released_results()

        self.assertEqual(rnds.send_pending(), {RndsSubmission.Status.SENT: 1})

        sent = RndsSubmission.objects.get(lab_result=first)
        self.assertEqual((sent.status, sent.rnds_id, sent.attempts), ("SENT", "abc123", 1))
        get.assert_called_once()
        self.assertEqual(
            get.call_args.kwargs["cert"], ("/run/secrets/rnds.crt", "/run/secrets/rnds.key")
        )
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], self.professional_cns)
        self.assertEqual(headers["X-Authorization-Server"], "Bearer tok")
        self.assertEqual(headers["Content-Type"], "application/fhir+json")
        self.assertIn("ehr-services.hmg.saude.gov.br", post.call_args.args[0])

        fixed = self.release(value="Detectável", supersedes=first)
        rnds.queue_released_results()
        post.return_value = _response(201, headers={"location": ".../Composition/def456"})
        rnds.send_pending()

        replacement = RndsSubmission.objects.get(lab_result=fixed)
        self.assertEqual(replacement.replaces, sent)
        self.assertEqual(replacement.document_key, sent.document_key)
        body = post.call_args.kwargs["data"].decode()
        self.assertIn('"targetReference": {"reference": "Composition/abc123"}', body)
        self.assertIn(str(sent.document_key), body)
        get.assert_called_once()  # token reaproveitado

    @mock.patch("apps.interoperability.rnds.requests.post")
    @mock.patch("apps.interoperability.rnds.requests.get")
    def test_refusal_is_retried_without_phi_and_401_renews_token(self, get, post):
        get.return_value = _response(200, json_body={"access_token": "tok"})
        post.return_value = _response(
            401,
            json_body={
                "issue": [
                    {
                        "code": "security",
                        "diagnostics": f"CNS {self.patient_cns} {self.patient.full_name}",
                    }
                ]
            },
        )
        self.release()
        rnds.queue_released_results()

        rnds.send_pending()

        failed = RndsSubmission.objects.get()
        self.assertEqual((failed.status, failed.attempts), ("FAILED", 1))
        self.assertEqual(failed.detail, "RNDS recusou o envio (HTTP 401: security).")
        self.assertIsNone(cache.get(rnds.TOKEN_CACHE_KEY))
        self.assertNotRegex(failed.detail, re.escape(self.patient_cns))

    @mock.patch("apps.interoperability.rnds.requests.post")
    @mock.patch("apps.interoperability.rnds.requests.get")
    def test_rectified_before_sending_goes_as_new_document(self, get, post):
        get.return_value = _response(200, json_body={"access_token": "tok"})
        post.return_value = _response(201, headers={"location": ".../Composition/new1"})
        first = self.release()
        rnds.queue_released_results()
        fixed = self.release(value="Detectável", supersedes=first)

        rnds.queue_released_results()
        rnds.send_pending()

        old, new = (RndsSubmission.objects.get(lab_result=r) for r in (first, fixed))
        self.assertEqual(
            (old.status, old.detail), ("BLOCKED", "Resultado retificado antes do envio.")
        )
        self.assertEqual((new.status, new.replaces), ("SENT", None))
        self.assertNotIn("relatesTo", post.call_args.kwargs["data"].decode())
        post.assert_called_once()

    @mock.patch("apps.interoperability.rnds.requests.post")
    def test_claimed_submission_is_not_sent_twice(self, post):
        self.release()
        rnds.queue_released_results()
        submission = RndsSubmission.objects.get()
        RndsSubmission.objects.filter(pk=submission.pk).update(status="SENDING")

        self.assertIsNone(rnds.send_submission(submission))
        post.assert_not_called()

    def test_command_dry_run_and_disabled_guard(self):
        self.release()
        self.release(value="Positivo")
        out = StringIO()
        call_command("rnds_send", "--dry-run", stdout=out)
        self.assertIn("1  Pronto para envio", out.getvalue())
        self.assertIn("1  Resultado qualitativo", out.getvalue())
        self.assertFalse(RndsSubmission.objects.exists())

        with self.settings(RNDS_ENABLED=False), self.assertRaises(CommandError):
            call_command("rnds_send", stdout=StringIO())


class RndsMasterDataTests(TestCase):
    def test_partial_rnds_coding_is_rejected(self):
        with self.assertRaises(ValidationError):
            LabTest.objects.create(
                code="PARCIAL", name="Parcial", specimen_type="Sangue", rnds_exam_code="COVID"
            )

    def test_professional_cns_is_validated(self):
        from aegis_med.tests.helpers import make_user

        with self.assertRaises(ValidationError):
            Employee.objects.create(
                user=make_user("rnds-prof", role="FUNC"),
                department="Lab",
                job_title="Técnico",
                cns="123",
            )
