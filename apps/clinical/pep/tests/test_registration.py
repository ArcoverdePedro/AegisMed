from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from aegis_med.tests.helpers import make_user

from ..models import Patient, PatientAccessGrant
from .test_views import TEST_STORAGES


@override_settings(STORAGES=TEST_STORAGES)
class PatientRegistrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin = make_user("reg-admin", role="ADM")
        admin.is_superuser = True
        admin.save(update_fields=["is_superuser"])
        cls.owner = make_user("reg-owner", role="FUNC")
        cls.other = make_user("reg-other", role="FUNC")
        cls.patient = Patient.objects.create(
            identifier_type=Patient.IdentifierType.OTHER,
            identifier="MRN-9",
            full_name="Ana Souza",
            birth_date=date(1990, 1, 2),
            created_by=cls.owner,
        )
        PatientAccessGrant.objects.create(
            patient=cls.patient, user=cls.owner, reason="Cadastro", granted_by=cls.owner
        )

    def data(self, **changes):
        return {
            "identifier_type": "OTHER",
            "identifier": "MRN-10",
            "full_name": "ana  souza",
            "birth_date": "1990-01-02",
            "sex": "U",
            "race_color": "99",
            "nationality": "BR",
            "cns": "898001160000001",
            "mother_name": "SEM INFORMAÇÃO",
            "state": "PE",
            "municipality_code": "2611606",
            **changes,
        }

    def test_sus_fields_are_required_on_forms(self):
        self.client.force_login(self.owner)
        url = reverse("pep:patient_create")

        response = self.client.post(url, self.data(cns="", mother_name="", municipality_code=""))
        form = response.context["form"]
        self.assertEqual(set(form.errors), {"cns", "mother_name", "municipality_code"})

        # identificador principal CNS dispensa repetir o numero no campo CNS
        response = self.client.post(
            url,
            self.data(
                identifier_type="CNS", identifier="700000000000005", cns="", confirm_new="on"
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Patient.objects.filter(cns="700000000000005").exists())

        # pacientes antigos podem ser atualizados sem os dados SUS ainda
        response = self.client.post(
            reverse("pep:patient_update", args=[self.patient.pk]),
            {"race_color": "99", "nationality": "BR", "phone": "81999990000"},
        )
        self.assertEqual(response.status_code, 302)

    def test_ethnicity_and_birth_country_are_conditional(self):
        patient = Patient.objects.get(pk=self.patient.pk)
        patient.race_color = Patient.RaceColor.INDIGENOUS
        patient.nationality = Patient.Nationality.FOREIGN
        patient.birth_country_code = "31"  # Brasil nao vale para estrangeiro
        with self.assertRaises(ValidationError) as ctx:
            patient.full_clean()
        self.assertIn("ethnicity_code", ctx.exception.message_dict)

        patient.ethnicity_code = "9999"
        with self.assertRaises(ValidationError) as ctx:
            patient.full_clean()
        self.assertIn("ethnicity_code", ctx.exception.message_dict)

        patient.ethnicity_code = "0001"
        with self.assertRaises(ValidationError) as ctx:
            patient.full_clean()
        self.assertIn("birth_country_code", ctx.exception.message_dict)

        patient.birth_country_code = "13"  # Argentina
        patient.full_clean()

        patient.race_color = Patient.RaceColor.BROWN
        patient.nationality = Patient.Nationality.BRAZILIAN
        patient.full_clean()
        self.assertEqual((patient.ethnicity_code, patient.birth_country_code), ("", ""))

    def test_sus_fields_validation(self):
        patient = Patient(
            identifier_type="OTHER",
            identifier="MRN-SUS",
            full_name="X",
            birth_date=date(2000, 1, 1),
            created_by=self.owner,
            cns="700 0000 0000 0005",
            mother_name=" Maria   da Silva ",
            state="PE",
            municipality_code="2611606",
        )
        patient.save()
        self.assertEqual((patient.cns, patient.mother_name), ("700000000000005", "Maria da Silva"))

        for field, value in [
            ("cns", "700000000000006"),
            ("municipality_code", "9999999"),
        ]:
            invalid = Patient.objects.get(pk=patient.pk)
            setattr(invalid, field, value)
            with self.assertRaises(ValidationError) as ctx:
                invalid.full_clean()
            self.assertIn(field, ctx.exception.message_dict)

    def test_municipality_search_and_city_state_from_ibge(self):
        self.client.force_login(self.owner)
        url = reverse("pep:municipality_options")
        response = self.client.get(url, {"municipality_code": "recif"})
        self.assertContains(response, '<option value="Recife/PE"></option>', html=True)
        self.assertNotContains(self.client.get(url, {"municipality_code": "r"}), "<option")

        # o nome escolhido na lista vira codigo IBGE; cidade e UF vem da tabela
        update = reverse("pep:patient_update", args=[self.patient.pk])
        sus = {"race_color": "99", "nationality": "BR", "state": "SP"}
        response = self.client.post(update, {**sus, "municipality_code": "sao jose da laje/al"})
        self.assertEqual(response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(
            (self.patient.municipality_code, self.patient.city, self.patient.state),
            ("2708303", "São José da Laje", "AL"),
        )
        self.assertContains(self.client.get(update), 'value="São José da Laje/AL"')

        response = self.client.post(update, {**sus, "municipality_code": "Recife"})
        self.assertIn("municipality_code", response.context["form"].errors)

    def test_cns_is_unique_across_primary_and_secondary(self):
        Patient.objects.create(
            identifier_type="CNS",
            identifier="700000000000005",
            full_name="Titular",
            birth_date=date(2000, 1, 1),
            created_by=self.owner,
        )
        other = Patient(
            identifier_type="OTHER",
            identifier="MRN-DUP",
            full_name="Outro",
            birth_date=date(2000, 1, 1),
            created_by=self.owner,
            cns="700000000000005",
        )
        with self.assertRaisesMessage(ValidationError, "CNS já cadastrado em outro paciente."):
            other.full_clean()

        conflicting = Patient(
            identifier_type="CNS",
            identifier="700000000000005",
            cns="898001160000001",
            full_name="Y",
            birth_date=date(2000, 1, 1),
            created_by=self.owner,
        )
        with self.assertRaises(ValidationError) as ctx:
            conflicting.clean()
        self.assertIn("cns", ctx.exception.message_dict)

    def test_cns_checksum(self):
        valid = Patient(
            identifier_type="CNS",
            identifier="700 0000 0000 0005",
            full_name="X",
            birth_date=date(2000, 1, 1),
            created_by=self.owner,
        )
        valid.full_clean()
        self.assertEqual(valid.identifier, "700000000000005")
        valid.identifier = "700000000000006"
        with self.assertRaises(ValidationError):
            valid.full_clean()

    def test_homonym_is_flagged_and_never_merged(self):
        self.client.force_login(self.owner)
        url = reverse("pep:patient_create")

        response = self.client.post(url, self.data())
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "MRN-9", status_code=409)
        self.assertEqual(Patient.objects.count(), 1)

        response = self.client.post(url, self.data(confirm_new="on"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.filter(full_name__iexact="Ana Souza").count(), 2)

    def test_duplicate_outside_scope_only_reveals_count(self):
        self.client.force_login(self.other)

        response = self.client.post(reverse("pep:patient_create"), self.data())

        self.assertContains(response, "1 cadastro(s)", status_code=409)
        self.assertNotContains(response, "MRN-9", status_code=409)

    def test_contact_update_keeps_identity_and_shows_social_name(self):
        self.client.force_login(self.owner)
        url = reverse("pep:patient_update", args=[self.patient.pk])

        response = self.client.post(
            url,
            {
                "social_name": " Ana  Lis ",
                "state": "pe",
                "city": "Recife",
                "identifier": "HACK",
                "cns": "700000000000005",
                "mother_name": "Maria Souza",
                "race_color": "03",
                "nationality": "BR",
                "municipality_code": "2611606",
            },
        )

        self.assertRedirects(response, reverse("pep:patient_detail", args=[self.patient.pk]))
        self.patient.refresh_from_db()
        self.assertEqual((self.patient.social_name, self.patient.state), ("Ana Lis", "PE"))
        self.assertEqual(self.patient.identifier, "MRN-9")
        self.assertEqual(
            (self.patient.cns, self.patient.race_color, self.patient.municipality_code),
            ("700000000000005", "03", "2611606"),
        )
        detail = self.client.get(response.url)
        self.assertContains(detail, "Parda")
        self.assertContains(detail, "Nome de registro: Ana Souza")
        self.assertContains(self.client.get(reverse("pep:patient_list") + "?q=Lis"), "Ana Lis")

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
