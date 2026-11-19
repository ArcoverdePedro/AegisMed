from django.test import TestCase
from django.urls import reverse

from .helpers import make_user


class WebSurfaceTests(TestCase):
    def setUp(self):
        self.admin = make_user("root", role="ADM")
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_superuser", "is_staff"])

    def test_health_endpoints_are_available_without_login(self):
        live = self.client.get(reverse("health_live"))
        ready = self.client.get(reverse("health_ready"))

        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json()["status"], "ok")
        self.assertEqual(ready.status_code, 200)
        self.assertTrue(ready.json()["checks"]["database"])
        self.assertTrue(ready.json()["checks"]["cache"])
