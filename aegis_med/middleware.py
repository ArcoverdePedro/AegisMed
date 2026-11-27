from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import patch_vary_headers

from .models import TrackedSession


class PrivateWorkflowMiddleware:
    """Nenhuma resposta fica no cache do navegador, salvo quem define o proprio Cache-Control.

    Estacao compartilhada: o botao Voltar apos o logout nao pode mostrar dados de paciente.
    Estaticos (WhiteNoise) e o PWA definem politica propria e ficam como estao.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not response.has_header("Cache-Control"):
            response["Cache-Control"] = "private, no-store, max-age=0"
            patch_vary_headers(response, ("Cookie", "HX-Request"))
        return response


class FirstAccessRedirectMiddleware:
    """Redireciona apenas enquanto a instalacao ainda nao possui administrador."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.User = get_user_model()
        self.setup_url = reverse("primeiro_cadastro")
        self._configured = False

    def __call__(self, request):
        if not self._configured:
            self._configured = self.User.objects.filter(is_superuser=True).exists()

        current_path = request.path
        bypass = current_path.startswith(
            (
                self.setup_url,
                "/static/",
                "/health/",
                "/manifest.webmanifest",
                "/service-worker.js",
                "/pwa/icons/",
                "/offline/",
            )
        )
        if not self._configured and not bypass:
            return redirect(self.setup_url)

        return self.get_response(request)


class CallPanelKioskMiddleware:
    """A conta da TV tem sessão longa, então só alcança o painel; o resto volta para ele."""

    ALLOWED_PREFIXES = (
        "/static/",
        "/health/",
        "/manifest.webmanifest",
        "/service-worker.js",
        "/pwa/icons/",
        "/offline/",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_paths = {
            reverse("scheduling:call_panel"),
            reverse("scheduling:call_panel_partial"),
            reverse("logout"),
        }

    def __call__(self, request):
        user = request.user
        if (
            user.is_authenticated
            and user.is_call_panel()
            and request.path not in self.allowed_paths
            and not request.path.startswith(self.ALLOWED_PREFIXES)
        ):
            return redirect("scheduling:call_panel")
        return self.get_response(request)


class TrackedSessionMiddleware:
    """Mantem inventario leve das sessoes autenticadas para revogacao pelo usuario."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            self._track(request)
        return self.get_response(request)

    def _track(self, request):
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        throttle_key = f"tracked-session:{session_key}"
        if cache.get(throttle_key):
            return

        TrackedSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                "user": request.user,
                "ip_address": request.META.get("REMOTE_ADDR") or None,
                "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:1000],
                "revoked_at": None,
            },
        )
        cache.set(throttle_key, True, 300)
