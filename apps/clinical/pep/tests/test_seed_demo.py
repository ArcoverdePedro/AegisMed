from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.clinical.adt.models import Admission, Discharge
from apps.clinical.pep.models import Patient
from apps.clinical.pep.validators import validate_cns


class SeedDemoTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_superuser(
            username="demo-admin", password="test-password", nivel_permissao="ADM"
        )

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo")

    @override_settings(DEBUG=True)
    def test_creates_valid_sus_patients_idempotently(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())

        patients = Patient.objects.filter(identifier_type=Patient.IdentifierType.CNS)
        self.assertEqual(patients.count(), 8)
        for patient in patients:
            validate_cns(patient.cns)
        self.assertEqual(Admission.objects.count(), 6)
        self.assertEqual(Discharge.objects.count(), 2)
