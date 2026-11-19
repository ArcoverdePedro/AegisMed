import uuid

from auditlog.registry import auditlog
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .sus_tables import BRAZIL_COUNTRY_CODE, table
from .validators import normalize_cpf, validate_cns, validate_cpf


class Patient(models.Model):
    class IdentifierType(models.TextChoices):
        CPF = "CPF", "CPF"
        CNS = "CNS", "Cartão Nacional de Saúde"
        OTHER = "OTHER", "Outro identificador"

    class Sex(models.TextChoices):
        FEMALE = "F", "Feminino"
        MALE = "M", "Masculino"
        INTERSEX = "I", "Intersexo"
        OTHER = "O", "Outro"
        UNKNOWN = "U", "Não informado"

    class RaceColor(models.TextChoices):
        """Codigos da tabela de raca/cor do SUS (Portaria MS 344/2017, BPA/AIH)."""

        WHITE = "01", "Branca"
        BLACK = "02", "Preta"
        BROWN = "03", "Parda"
        YELLOW = "04", "Amarela"
        INDIGENOUS = "05", "Indígena"
        UNKNOWN = "99", "Sem informação"

    class Nationality(models.TextChoices):
        BRAZILIAN = "BR", "Brasileira"
        NATURALIZED = "NAT", "Naturalizada"
        FOREIGN = "EST", "Estrangeira"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier_type = models.CharField(
        max_length=10,
        choices=IdentifierType.choices,
        default=IdentifierType.CPF,
    )
    identifier = models.CharField(max_length=64)
    full_name = models.CharField(max_length=255)
    social_name = models.CharField(max_length=255, blank=True)
    birth_date = models.DateField()
    sex = models.CharField(max_length=1, choices=Sex.choices, default=Sex.UNKNOWN)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    postal_code = models.CharField(max_length=9, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=2, blank=True)
    # 18 aceita a forma digitada com espacos; clean() grava so os 15 digitos.
    cns = models.CharField("CNS", max_length=18, blank=True)
    mother_name = models.CharField("Nome da mãe", max_length=255, blank=True)
    race_color = models.CharField(
        "Raça/cor", max_length=2, choices=RaceColor.choices, default=RaceColor.UNKNOWN
    )
    nationality = models.CharField(
        "Nacionalidade", max_length=3, choices=Nationality.choices, default=Nationality.BRAZILIAN
    )
    municipality_code = models.CharField("Código IBGE do município", max_length=7, blank=True)
    ethnicity_code = models.CharField("Etnia indígena (código SUS)", max_length=4, blank=True)
    birth_country_code = models.CharField(
        "País de nascimento (código SUS)", max_length=3, blank=True
    )
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_patients",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name", "birth_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["identifier_type", "identifier"],
                name="uniq_pep_patient_identifier",
            ),
            models.UniqueConstraint(
                fields=["cns"],
                condition=~models.Q(cns=""),
                name="uniq_pep_patient_cns",
                violation_error_message="CNS já cadastrado em outro paciente.",
            ),
        ]
        indexes = [
            models.Index(fields=["full_name"], name="pep_patient_name_idx"),
            models.Index(fields=["birth_date"], name="pep_patient_birth_idx"),
            models.Index(fields=["active"], name="pep_patient_active_idx"),
        ]

    def clean(self):
        super().clean()
        self.identifier = (self.identifier or "").strip()
        self.full_name = " ".join((self.full_name or "").split())

        self.social_name = " ".join((self.social_name or "").split())
        self.state = (self.state or "").strip().upper()

        if self.identifier_type == self.IdentifierType.CPF:
            self.identifier = normalize_cpf(self.identifier)
            validate_cpf(self.identifier)
        elif self.identifier_type == self.IdentifierType.CNS:
            self.identifier = normalize_cpf(self.identifier)
            validate_cns(self.identifier)

        self.cns = normalize_cpf(self.cns)
        if self.identifier_type == self.IdentifierType.CNS:
            if self.cns and self.cns != self.identifier:
                raise ValidationError({"cns": "CNS difere do identificador principal."})
            self.cns = self.identifier
        elif self.cns:
            try:
                validate_cns(self.cns)
            except ValidationError as error:
                raise ValidationError({"cns": error.messages}) from error

        self.mother_name = " ".join((self.mother_name or "").split())
        self.municipality_code = normalize_cpf(self.municipality_code)
        if self.municipality_code:
            municipality = table("municipios").get(self.municipality_code)
            if municipality is None:
                raise ValidationError({"municipality_code": "Código IBGE do município inválido."})
            self.city, self.state = municipality["nome"], municipality["uf"]

        self.ethnicity_code = (self.ethnicity_code or "").strip()
        if self.race_color != self.RaceColor.INDIGENOUS:
            self.ethnicity_code = ""
        elif self.ethnicity_code not in table("etnias"):
            raise ValidationError({"ethnicity_code": "Informe a etnia para raça/cor indígena."})

        self.birth_country_code = (self.birth_country_code or "").strip()
        if self.nationality == self.Nationality.BRAZILIAN:
            self.birth_country_code = ""
        elif (
            self.birth_country_code not in table("paises")
            or self.birth_country_code == BRAZIL_COUNTRY_CODE
        ):
            raise ValidationError(
                {"birth_country_code": "Informe o país de nascimento (exceto Brasil)."}
            )

        if self.birth_date and self.birth_date > timezone.localdate():
            raise ValidationError({"birth_date": "A data de nascimento não pode estar no futuro."})

        if not self.full_name:
            raise ValidationError({"full_name": "Informe o nome do paciente."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Paciente {self.id}"

    @property
    def ethnicity_name(self):
        return table("etnias").get(self.ethnicity_code, {}).get("nome", "")

    @property
    def birth_country_name(self):
        return table("paises").get(self.birth_country_code, {}).get("nome", "")

    @property
    def display_name(self):
        """Nome social tem precedencia no atendimento (Decreto 8.727/2016)."""
        return self.social_name or self.full_name

    def possible_duplicates(self):
        """Mesmo nome e nascimento; homonimos nunca sao unidos automaticamente."""
        return Patient.objects.filter(
            full_name__iexact=self.full_name, birth_date=self.birth_date
        ).exclude(pk=self.pk)


class PatientAccessGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="access_grants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_access_grants",
    )
    reason = models.CharField(max_length=255)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="granted_patient_accesses",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "user"],
                name="uniq_pep_patient_access_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "expires_at"], name="pep_access_user_exp_idx"),
            models.Index(
                fields=["patient", "expires_at"],
                name="pep_access_patient_exp_idx",
            ),
        ]

    @property
    def is_active(self):
        return self.expires_at is None or self.expires_at > timezone.now()

    def clean(self):
        super().clean()
        self.reason = " ".join((self.reason or "").split())
        if not self.reason:
            raise ValidationError({"reason": "Informe a justificativa do acesso."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Acesso PEP {self.id}"


class Encounter(models.Model):
    class Type(models.TextChoices):
        CONSULTATION = "CONSULTATION", "Consulta"
        EMERGENCY = "EMERGENCY", "Urgência/Emergência"
        INPATIENT = "INPATIENT", "Internação"
        TELEHEALTH = "TELEHEALTH", "Teleatendimento"
        OTHER = "OTHER", "Outro"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberto"
        CLOSED = "CLOSED", "Encerrado"
        CANCELLED = "CANCELLED", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="encounters",
    )
    encounter_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.CONSULTATION,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=160, blank=True)
    reason = models.TextField(blank=True)
    responsible_professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="responsible_pep_encounters",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_pep_encounters",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["patient", "started_at"], name="pep_enc_patient_start_idx"),
            models.Index(fields=["status"], name="pep_enc_status_idx"),
            models.Index(
                fields=["responsible_professional", "started_at"],
                name="pep_enc_prof_start_idx",
            ),
        ]

    def clean(self):
        super().clean()
        self.location = " ".join((self.location or "").split())
        self.reason = " ".join((self.reason or "").split())

        if self.started_at and self.ended_at and self.ended_at < self.started_at:
            raise ValidationError({"ended_at": "O encerramento não pode ser anterior ao início."})
        if self.status == self.Status.CLOSED and not self.ended_at:
            raise ValidationError({"ended_at": "Informe o horário de encerramento do encontro."})
        if self.status == self.Status.OPEN and self.ended_at:
            raise ValidationError(
                {"ended_at": "Encontro aberto não pode possuir horário de encerramento."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Encontro {self.id}"


class ClinicalEvolution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.PROTECT,
        related_name="evolutions",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_evolutions",
    )
    content = models.TextField()
    amendment_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="amendments",
        null=True,
        blank=True,
    )
    amendment_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["encounter", "created_at"],
                name="pep_evo_enc_created_idx",
            ),
            models.Index(
                fields=["author", "created_at"],
                name="pep_evo_author_created_idx",
            ),
        ]

    def clean(self):
        super().clean()
        self.content = (self.content or "").strip()
        self.amendment_reason = " ".join((self.amendment_reason or "").split())

        if not self.content:
            raise ValidationError({"content": "Informe o conteúdo da evolução clínica."})

        if self.encounter_id and self.encounter.status != Encounter.Status.OPEN:
            raise ValidationError(
                {"encounter": "Evoluções só podem ser registradas em encontro aberto."}
            )

        if self.amendment_of_id:
            if self.amendment_of_id == self.id:
                raise ValidationError(
                    {"amendment_of": "Uma evolução não pode corrigir a si própria."}
                )
            if self.amendment_of.encounter_id != self.encounter_id:
                raise ValidationError(
                    {
                        "amendment_of": (
                            "O adendo deve pertencer ao mesmo encontro da evolução original."
                        )
                    }
                )
            if not self.amendment_reason:
                raise ValidationError({"amendment_reason": "Informe o motivo do adendo."})
        elif self.amendment_reason:
            raise ValidationError(
                {
                    "amendment_reason": (
                        "Motivo de adendo só pode ser informado ao corrigir uma evolução."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Evoluções clínicas são imutáveis. Registre um adendo em vez de editar."
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Evoluções clínicas são imutáveis e não podem ser excluídas.")

    def __str__(self):
        return f"Evolução {self.id}"


class ProblemListEntry(models.Model):
    """Lista de problemas em texto livre; codigo so com sistema e versao informados (sem inferencia)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativo"
        RESOLVED = "RESOLVED", "Resolvido"
        ENTERED_IN_ERROR = "ERROR", "Registrado por engano"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="problems")
    encounter = models.ForeignKey(
        Encounter, null=True, blank=True, on_delete=models.PROTECT, related_name="problems"
    )
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    onset_date = models.DateField(null=True, blank=True)
    code_system = models.CharField(max_length=40, blank=True)
    code = models.CharField(max_length=20, blank=True)
    code_version = models.CharField(max_length=20, blank=True)
    supersedes = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )
    reason = models.CharField(max_length=255, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at", "-id"]

    def __str__(self):
        return f"Problema {self.pk}"

    def clean(self):
        super().clean()
        self.description = " ".join((self.description or "").split())
        self.reason = " ".join((self.reason or "").split())
        if not self.description:
            raise ValidationError({"description": "Descreva o problema."})
        if self.code and not (self.code_system and self.code_version):
            raise ValidationError({"code": "Código exige sistema e versão de origem."})
        if self.supersedes_id:
            if self.supersedes.patient_id != self.patient_id:
                raise ValidationError({"supersedes": "Revisão deve ser do mesmo paciente."})
            if not self.reason:
                raise ValidationError({"reason": "Informe o motivo da revisão."})
        if self.onset_date and self.onset_date > timezone.localdate():
            raise ValidationError({"onset_date": "Início não pode estar no futuro."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Problemas são versionados: registre uma revisão.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Problemas não podem ser excluídos.")


auditlog.register(
    Patient,
    exclude_fields=[
        "identifier",
        "full_name",
        "birth_date",
        "phone",
        "email",
        "cns",
        "mother_name",
        "race_color",  # dado sensivel (LGPD art. 5, II)
        "ethnicity_code",
    ],
    mask_fields=[
        "social_name",
        "postal_code",
        "address",
        "city",
        "state",
        "nationality",
        "municipality_code",
        "birth_country_code",
    ],
)
auditlog.register(PatientAccessGrant, exclude_fields=["reason"])
auditlog.register(Encounter, exclude_fields=["reason", "location"])
auditlog.register(
    ClinicalEvolution,
    exclude_fields=["content", "amendment_reason"],
)
auditlog.register(ProblemListEntry, exclude_fields=["description", "reason"])
