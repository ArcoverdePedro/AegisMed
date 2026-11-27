import uuid

from auditlog.registry import auditlog
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PatientExportReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey("pep.Patient", on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    contract_version = models.CharField(max_length=32, default="patient-r4-v1", editable=False)
    content_sha256 = models.CharField(max_length=64, editable=False)

    class Meta:
        permissions = [("export_patient", "Pode exportar cadastro mínimo de paciente")]

    def __str__(self):
        return f"Exportação {self.pk}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Recibos de exportação são imutáveis.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Recibos de exportação não podem ser excluídos.")


auditlog.register(PatientExportReceipt)


class LaboratorySource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField("Código técnico", max_length=64, unique=True)
    label = models.CharField("Descrição técnica", max_length=160)
    active = models.BooleanField("Ativa", default=True)
    operators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"Origem {self.pk}"

    def clean(self):
        for field in ("code", "label"):
            value = getattr(self, field).strip()
            if not value:
                raise ValidationError({field: "Este campo é obrigatório."})
            setattr(self, field, value)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class LaboratoryInboxReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(LaboratorySource, on_delete=models.PROTECT)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    received_at = models.DateTimeField(auto_now_add=True)
    size = models.PositiveIntegerField()
    plaintext_sha256 = models.CharField(max_length=64)
    ciphertext_sha256 = models.CharField(max_length=64)
    ciphertext = models.BinaryField()
    wrapped_key = models.TextField()
    encryption_version = models.CharField(max_length=16, default="aegis1", editable=False)

    class Meta:
        ordering = ["-received_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "plaintext_sha256"],
                name="uniq_lab_source_digest",
            )
        ]
        indexes = [models.Index(fields=["-received_at", "-id"], name="lab_inbox_received_idx")]
        permissions = [
            ("view_lab_inbox", "Pode consultar caixa laboratorial"),
            ("receive_lab_file", "Pode receber arquivo laboratorial"),
        ]

    def __str__(self):
        return f"Recebimento {self.pk}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Recibos de recebimento são imutáveis.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Recibos não podem ser excluídos.")


auditlog.register(LaboratorySource, exclude_fields=["label"], m2m_fields={"operators"})
auditlog.register(
    LaboratoryInboxReceipt,
    exclude_fields=[
        "ciphertext",
        "wrapped_key",
        "plaintext_sha256",
        "ciphertext_sha256",
    ],
)


class RndsSubmission(models.Model):
    """Envio de um resultado liberado à RNDS; guarda só metadados técnicos, sem PHI."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Aguardando envio"
        SENDING = "SENDING", "Enviando"
        SENT = "SENT", "Enviado"
        FAILED = "FAILED", "Falhou (nova tentativa)"
        BLOCKED = "BLOCKED", "Bloqueado (faltam dados)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab_result = models.OneToOneField(
        "lis.LabResult", on_delete=models.PROTECT, related_name="rnds_submission"
    )
    replaces = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="replaced_by"
    )
    # Bundle.identifier.value: o mesmo no documento original e nas substituições.
    document_key = models.UUIDField(default=uuid.uuid4, editable=False)
    environment = models.CharField(max_length=4)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    detail = models.CharField("Motivo técnico", max_length=255, blank=True)
    rnds_id = models.CharField("Código RNDS", max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "updated_at"], name="rnds_status_idx")]
        verbose_name = "Envio RNDS"
        verbose_name_plural = "Envios RNDS"

    def __str__(self):
        return f"Envio RNDS {self.pk}"

    def delete(self, *args, **kwargs):
        raise ValidationError("Envios RNDS não podem ser excluídos.")


auditlog.register(RndsSubmission)
