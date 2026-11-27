from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from aegis_med.forms import FirstUserForm
from aegis_med.models import CALL_PANEL_SESSION_SECONDS, CALL_PANEL_USERNAME
from aegis_med.tests.helpers import make_user
from apps.clinical.pep.tests.test_views import TEST_STORAGES

User = get_user_model()
TV_PASSWORD = "Tela-Recepcao-2026!"


@override_settings(STORAGES=TEST_STORAGES, SECURE_SSL_REDIRECT=False)
class CallPanelAccountTests(TestCase):
    def _set_tv_password(self, client, password=TV_PASSWORD):
        return client.post(
            reverse("scheduling:call_panel_account"),
            {"new_password1": password, "new_password2": password},
        )

    def _make_admin(self):
        admin = make_user("tv-admin", role="ADM")
        admin.is_superuser = True
        admin.save(update_fields=["is_superuser"])
        return admin

    def test_first_setup_continues_to_tv_password_step(self):
        response = self.client.post(
            reverse("primeiro_cadastro"),
            {
                "first_name": "Ana",
                "last_name": "Admin",
                "username": "ana.admin",
                "email": "ana@example.com",
                "telefone": "(81) 99999-0000",
                "password1": "Admin-Forte-2026!",
                "password2": "Admin-Forte-2026!",
            },
        )
        self.assertRedirects(
            response,
            f"{reverse('scheduling:call_panel_account')}?inicio=1",
            fetch_redirect_response=False,
        )
        self.assertContains(self.client.get(response["Location"]), CALL_PANEL_USERNAME)

        self._set_tv_password(self.client)

        tv = User.objects.get(username=CALL_PANEL_USERNAME)
        self.assertTrue(tv.check_password(TV_PASSWORD))
        self.assertEqual(tv.nivel_permissao, "FUNC")
        self.assertFalse(tv.is_superuser or tv.is_staff)
        self.assertEqual(
            list(tv.user_permissions.values_list("codename", flat=True)), ["view_call_panel"]
        )

    def test_username_is_reserved(self):
        form = FirstUserForm(data={"username": CALL_PANEL_USERNAME})
        self.assertIn("username", form.errors)

    def test_only_admin_sets_tv_password(self):
        self._make_admin()
        self.client.force_login(make_user("tv-employee", role="FUNC"))
        self.assertEqual(self._set_tv_password(self.client).status_code, 403)

    def test_menu_link_only_for_admin(self):
        url = reverse("scheduling:call_panel_account")
        admin = self._make_admin()
        self.client.force_login(make_user("tv-employee", role="FUNC"))
        self.assertNotContains(self.client.get(reverse("home")), url)
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse("home")), url)

    def test_tv_session_is_persistent_locked_to_panel_and_ends_on_password_change(self):
        admin = self._make_admin()
        self.client.force_login(admin)
        self._set_tv_password(self.client)

        tv = self.client_class()
        response = tv.post(
            reverse("login"), {"username": CALL_PANEL_USERNAME, "password": TV_PASSWORD}
        )
        self.assertRedirects(response, reverse("scheduling:call_panel"))
        self.assertEqual(tv.session.get_expiry_age(), CALL_PANEL_SESSION_SECONDS)
        self.assertFalse(tv.session.get_expire_at_browser_close())

        for blocked in ("home", "cadastro", "scheduling:queue", "security_settings"):
            self.assertRedirects(
                tv.get(reverse(blocked)),
                reverse("scheduling:call_panel"),
                fetch_redirect_response=False,
            )

        self._set_tv_password(self.client, "Outra-Senha-TV-2026!")
        self.assertEqual(tv.get(reverse("scheduling:call_panel")).status_code, 302)
