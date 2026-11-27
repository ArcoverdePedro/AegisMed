import uuid
from datetime import date, time, timedelta
from unittest import mock

from asgiref.sync import async_to_sync
from django.contrib.auth.models import Permission
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aegis_med.tests.helpers import make_user
from apps.clinical.pep.models import Patient
from apps.clinical.pep.tests.test_views import TEST_STORAGES

from ..consumers import CallPanelConsumer
from ..services import CALL_PANEL_GROUP, book_appointment, call_patient, check_in, create_slots
from .test_scheduling import grant


@override_settings(STORAGES=TEST_STORAGES, SECURE_SSL_REDIRECT=False)
class CallPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin = make_user("panel-admin", role="ADM")
        admin.is_superuser = True
        admin.save(update_fields=["is_superuser"])
        cls.reception = make_user("panel-reception", role="FUNC")
        grant(
            cls.reception, "view_agenda", "manage_agenda", "book_appointment", "checkin_appointment"
        )
        cls.tv = make_user("panel-tv", role="FUNC")
        grant(cls.tv, "view_call_panel")
        doctor = make_user("panel-doctor", role="FUNC")
        grant(doctor, "view_agenda")
        cls.slots = create_slots(
            user=cls.reception,
            professional=doctor,
            day=timezone.localdate() + timedelta(days=1),
            start=time(8, 0),
            end=time(9, 0),
            minutes=30,
            capacity=1,
            location="Consultório 7",
        )
        cls.patients = [
            Patient.objects.create(
                identifier_type="OTHER",
                identifier=f"PANEL-{n}",
                full_name=name,
                birth_date=date(1980, 1, 1),
                created_by=cls.reception,
            )
            for n, name in enumerate(["Helena Prado", "Otávio Reis"])
        ]

    def _arrive(self, slot, patient):
        appointment = book_appointment(
            user=self.reception, slot=slot, patient=patient, operation_key=uuid.uuid4()
        )
        return check_in(user=self.reception, appointment=appointment)

    def test_panel_requires_its_own_permission(self):
        self.client.force_login(self.reception)
        self.assertEqual(self.client.get(reverse("scheduling:call_panel")).status_code, 403)
        self.assertEqual(self.client.get(reverse("scheduling:call_panel_partial")).status_code, 403)

        self.client.logout()
        self.assertEqual(self.client.get(reverse("scheduling:call_panel")).status_code, 302)
        expired = self.client.get(reverse("scheduling:call_panel_partial"))
        self.assertEqual(expired["HX-Refresh"], "true")

    def test_panel_shows_only_ticket_and_location_of_called(self):
        called = call_patient(user=self.reception, appointment=self._arrive(*self._pair(0)))
        waiting = self._arrive(*self._pair(1))
        self.client.force_login(self.tv)

        body = self.client.get(reverse("scheduling:call_panel")).content.decode()

        self.assertIn(called.ticket, body)
        self.assertIn("Consultório 7", body)
        self.assertNotIn(waiting.ticket, body)
        for patient in self.patients:
            self.assertNotIn(patient.full_name, body)
        self.assertNotIn("panel-doctor", body)

    def test_call_sends_signal_without_data(self):
        appointment = self._arrive(*self._pair(0))
        with mock.patch("apps.clinical.scheduling.services.send_after_commit") as send:
            call_patient(user=self.reception, appointment=appointment)
        send.assert_called_once_with(CALL_PANEL_GROUP, {"type": "call_panel_refresh"})

    def _pair(self, index):
        return self.slots[index], self.patients[index]


class CallPanelConsumerTests(TransactionTestCase):
    def test_permission_is_revalidated_from_database(self):
        tv = make_user("panel-socket-tv", role="FUNC")
        grant(tv, "view_call_panel")
        consumer = CallPanelConsumer()
        consumer.user = tv
        self.assertTrue(async_to_sync(consumer.user_can_view_call_panel)())

        tv.user_permissions.remove(
            Permission.objects.get(content_type__app_label="scheduling", codename="view_call_panel")
        )
        self.assertFalse(async_to_sync(consumer.user_can_view_call_panel)())

        grant(tv, "view_call_panel")
        tv.is_active = False
        tv.save(update_fields=["is_active"])
        self.assertFalse(async_to_sync(consumer.user_can_view_call_panel)())
