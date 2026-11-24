from django.urls import path

from apps.pwa.views import PwaLogoutView

from .web import auth, dashboard, health, security

urlpatterns = [
    path("setup/", auth.FirstSuperuserCreateView.as_view(), name="primeiro_cadastro"),
    path("", dashboard.home, name="home"),
    path("dashboard/", dashboard.dashboard, name="dashboard"),
    path("auditoria/", dashboard.audit_log, name="audit_log"),
    path("sobre/", dashboard.sobre, name="sobre"),
    path("login/", auth.custom_login, name="login"),
    path("login/2fa/", auth.login_2fa, name="login_2fa"),
    path("logout/", PwaLogoutView.as_view(), name="logout"),
    path("cadastro/", auth.cadastro, name="cadastro"),
    path("user/", auth.user_profile, name="user"),
    path("seguranca/", security.security_settings, name="security_settings"),
    path("seguranca/2fa/iniciar/", security.begin_2fa, name="begin_2fa"),
    path("seguranca/2fa/ativar/", security.enable_2fa, name="enable_2fa"),
    path("seguranca/2fa/desativar/", security.disable_2fa, name="disable_2fa"),
    path(
        "seguranca/sessoes/<int:session_id>/revogar/",
        security.revoke_session,
        name="revoke_session",
    ),
    path(
        "seguranca/sessoes/revogar-outras/",
        security.revoke_other_sessions,
        name="revoke_other_sessions",
    ),
    path("health/live/", health.live, name="health_live"),
    path("health/ready/", health.ready, name="health_ready"),
]
