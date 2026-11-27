import uuid

from auditlog.registry import auditlog
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

# Conta fixa da TV do painel de chamada: o nome é padrão, só a senha é definida pelo admin.
CALL_PANEL_USERNAME = "aegis.expositor"
# shortcut: "nunca expira" = 10 anos; troca de senha ou revogação encerram a sessão.
CALL_PANEL_SESSION_SECONDS = 10 * 365 * 24 * 60 * 60


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    NIVEL_PERMISSAO_CHOICES = [
        ("ADM", "Administrador"),
        ("FUNC", "Funcionário"),
        ("CLI", "Cliente"),
    ]

    foto_perfil = models.TextField(null=True, blank=True)
    telefone = models.CharField(max_length=16, null=True, blank=True)
    nivel_permissao = models.CharField(
        max_length=4,
        choices=NIVEL_PERMISSAO_CHOICES,
        default="CLI",
        verbose_name="Nível de Permissão",
    )

    def is_admin(self):
        return self.nivel_permissao == "ADM" or self.is_superuser

    def is_employee(self):
        return self.nivel_permissao == "FUNC"

    def is_client(self):
        return self.nivel_permissao == "CLI"

    def is_call_panel(self):
        return self.username == CALL_PANEL_USERNAME

    def __str__(self):
        return f"{self.username} ({self.nivel_permissao})"


class UserSecuritySettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_settings",
    )
    totp_secret_encrypted = models.TextField(blank=True)
    totp_enabled = models.BooleanField(default=False)
    recovery_codes = models.JSONField(default=list, blank=True)
    # Janela TOTP do ultimo codigo aceito: o mesmo codigo nao entra duas vezes.
    totp_last_timestep = models.BigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class TrackedSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tracked_sessions",
    )
    session_key = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]


auditlog.register(
    CustomUser,
    exclude_fields=["password", "last_login", "foto_perfil"],
    mask_fields=["email", "telefone"],
)
auditlog.register(
    UserSecuritySettings,
    exclude_fields=["totp_secret_encrypted", "recovery_codes", "totp_last_timestep"],
)
auditlog.register(TrackedSession, exclude_fields=["session_key"])
