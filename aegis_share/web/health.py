from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def live(request):
    return JsonResponse({"status": "ok", "service": "aegisshare"})


@require_GET
def ready(request):
    checks = {"database": False, "cache": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone()[0] == 1
    except Exception:
        checks["database"] = False

    try:
        cache.set("healthcheck", "ok", 10)
        checks["cache"] = cache.get("healthcheck") == "ok"
    except Exception:
        checks["cache"] = False

    healthy = all(checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "error", "checks": checks}, status=200 if healthy else 503
    )


@require_GET
def services(request):
    checks = {"database": True, "redis_configured": bool(settings.REDIS_URL)}
    return JsonResponse({"status": "ok", "checks": checks})
