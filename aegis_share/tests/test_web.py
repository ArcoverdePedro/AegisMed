import re

from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import make_user
from .test_security import TEST_STORAGES


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

    @override_settings(STORAGES=TEST_STORAGES)
    def test_csp_allows_only_inline_scripts_with_the_request_nonce(self):
        response = self.client.get(reverse("home"))

        policy = response["Content-Security-Policy"]
        nonce = re.search(r"'nonce-([^']+)'", policy).group(1)
        self.assertIn("script-src 'self' 'nonce-", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        inline = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", response.content.decode())
        self.assertTrue(inline)
        for attrs in inline:
            self.assertIn(f'nonce="{nonce}"', attrs)
