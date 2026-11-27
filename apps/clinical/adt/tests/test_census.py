import datetime as dt
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.clinical.pep.models import Encounter, Patient

from ..lifecycle import discharge_patient
from ..models import Bed, Discharge, Location, UserLocationAccess
from ..services import admit_patient
from .test_views import TEST_STORAGES

User = get_user_model()


@override_settings(STORAGES=TEST_STORAGES)
class HospitalCensusTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="census-admin", password="test-password", nivel_permissao="ADM"
        )
        self.employee = User.objects.create_user(
            username="census-employee", password="test-password", nivel_permissao="FUNC"
        )
        location = Location.objects.create(
            code="CENSO-01", name="Setor Censo", kind=Location.Kind.WARD
        )
        bed = Bed.objects.create(location=location, code="01", label="Leito 01")
        Bed.objects.create(
            location=location,
            code="02",
            label="Leito 02",
            operational_status=Bed.OperationalStatus.BLOCKED,
        )
        UserLocationAccess.objects.create(
            user=self.employee, location=location, granted_by=self.admin
        )

        tz = timezone.get_current_timezone()
        self.today = timezone.localdate()
        admitted_at = dt.datetime.combine(self.today - dt.timedelta(days=3), dt.time(10), tz)
        patient = Patient.objects.create(
            identifier_type=Patient.IdentifierType.OTHER,
            identifier="CENSO-PATIENT",
            full_name="Paciente Censo",
            birth_date=self.today - dt.timedelta(days=365 * 50),
            created_by=self.admin,
        )
        encounter = Encounter.objects.create(
            patient=patient,
            encounter_type=Encounter.Type.INPATIENT,
            started_at=admitted_at,
            responsible_professional=self.admin,
            created_by=self.admin,
        )
        admission = admit_patient(
            encounter_id=encounter.pk,
            bed_id=bed.pk,
            actor=self.admin,
            admitted_at=admitted_at,
            operation_key=uuid.uuid4(),
        )
        discharge_patient(
            admission_id=admission.pk,
            disposition=Discharge.Disposition.HOME,
            actor=self.admin,
            operation_key=uuid.uuid4(),
            discharged_at=dt.datetime.combine(self.today - dt.timedelta(days=1), dt.time(15), tz),
        )

    def _params(self, **extra):
        return {
            "start": (self.today - dt.timedelta(days=3)).isoformat(),
            "end": (self.today - dt.timedelta(days=1)).isoformat(),
            **extra,
        }

    def test_requires_view_admission_permission(self):
        self.client.force_login(self.employee)

        response = self.client.get(reverse("adt:census"), self._params())

        self.assertEqual(response.status_code, 403)

    def test_indicators_follow_ms_definitions(self):
        self.employee.user_permissions.add(
            Permission.objects.get(codename="view_admission", content_type__app_label="adt")
        )
        self.client.force_login(self.employee)

        response = self.client.get(reverse("adt:census"), self._params())

        indicators = response.context["indicators"]
        # Três dias de período, um leito operacional (o bloqueado não conta).
        self.assertEqual(indicators["Leitos operacionais"], 1)
        self.assertEqual(indicators["Leito-dia"], 3)
        # Internado no dia 1 e saiu no dia 3: presente nos censos das noites 1 e 2.
        self.assertEqual(indicators["Paciente-dia"], 2)
        self.assertEqual(indicators["Saídas"], 1)
        self.assertEqual(indicators["Taxa de ocupação (%)"], 66.67)
        self.assertEqual(indicators["Média de permanência (dias)"], 2.0)
        self.assertEqual(indicators["Taxa de mortalidade hospitalar (%)"], 0.0)

        csv_response = self.client.get(reverse("adt:census"), self._params(formato="csv"))
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("Paciente-dia,2", csv_response.content.decode())
