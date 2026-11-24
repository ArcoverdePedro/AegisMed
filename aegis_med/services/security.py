import hashlib
import secrets

import pyotp
from django.core.cache import cache
from django.db import transaction

from aegis_med.models import UserSecuritySettings

from .crypto import decrypt_secret, encrypt_secret


def too_many_attempts(key: str, limit: int, window_seconds: int = 300) -> bool:
    """Conta mais uma tentativa e diz se o limite foi passado.

    `incr` e atomico no cache, entao requisicoes em paralelo nao leem o mesmo valor.
    """
    cache.add(key, 0, window_seconds)
    try:
        attempts = cache.incr(key)
    except ValueError:  # a chave expirou entre o add e o incr
        cache.set(key, 1, window_seconds)
        attempts = 1
    return attempts > limit


def _security_settings(user):
    obj, _ = UserSecuritySettings.objects.get_or_create(user=user)
    return obj


def begin_totp_setup(user):
    security = _security_settings(user)
    secret = pyotp.random_base32()
    security.totp_secret_encrypted = encrypt_secret(secret, purpose=f"totp:{user.id}")
    security.totp_enabled = False
    security.recovery_codes = []
    security.save()
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.email or user.username,
        issuer_name="AegisMed",
    )
    return secret, uri


def verify_totp(user, code: str) -> bool:
    try:
        security = user.security_settings
    except UserSecuritySettings.DoesNotExist:
        return False
    if not security.totp_secret_encrypted:
        return False
    secret = decrypt_secret(
        security.totp_secret_encrypted,
        purpose=f"totp:{user.id}",
    )
    return pyotp.TOTP(secret).verify((code or "").strip(), valid_window=1)


def enable_totp(user, code: str):
    security = _security_settings(user)
    if not verify_totp(user, code):
        raise ValueError("Codigo TOTP invalido.")

    recovery_plain = [secrets.token_hex(5).upper() for _ in range(8)]
    security.recovery_codes = [hashlib.sha256(code.encode()).hexdigest() for code in recovery_plain]
    security.totp_enabled = True
    security.save(update_fields=["totp_enabled", "recovery_codes", "updated_at"])
    return recovery_plain


def disable_totp(user):
    security = _security_settings(user)
    security.totp_enabled = False
    security.totp_secret_encrypted = ""
    security.recovery_codes = []
    security.save()


@transaction.atomic
def consume_recovery_code(user, code: str) -> bool:
    _security_settings(user)
    # Trava a linha: dois logins ao mesmo tempo nao podem usar o mesmo codigo.
    security = UserSecuritySettings.objects.select_for_update().get(user=user)
    candidate = hashlib.sha256((code or "").strip().upper().encode()).hexdigest()
    if candidate not in security.recovery_codes:
        return False
    security.recovery_codes.remove(candidate)
    security.save(update_fields=["recovery_codes", "updated_at"])
    return True
