from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils import timezone

from . import sus_tables
from .models import ClinicalEvolution, Encounter, Patient, ProblemListEntry

SUS_FIELDS = [
    "cns",
    "mother_name",
    "race_color",
    "ethnicity_code",
    "nationality",
    "birth_country_code",
    "municipality_code",
]
CONTACT_FIELDS = ["social_name", "phone", "email", "postal_code", "address", *SUS_FIELDS]
CONTACT_WIDGETS = {
    "cns": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "maxlength": "18"}),
    "mother_name": forms.TextInput(attrs={"class": "input", "maxlength": "255"}),
    "race_color": forms.Select(),
    "nationality": forms.Select(),
    "ethnicity_code": forms.Select(),
    "birth_country_code": forms.Select(),
    "municipality_code": forms.TextInput(
        attrs={
            "class": "input",
            "list": "municipality-options",
            "autocomplete": "off",
            "placeholder": "Digite o nome, ex.: Recife",
            "hx-get": reverse_lazy("pep:municipality_options"),
            "hx-trigger": "input changed delay:300ms",
            "hx-target": "#municipality-options",
        }
    ),
    "social_name": forms.TextInput(attrs={"class": "input", "maxlength": "255"}),
    "postal_code": forms.TextInput(
        attrs={"class": "input", "autocomplete": "postal-code", "maxlength": "9"}
    ),
    "address": forms.TextInput(
        attrs={"class": "input", "autocomplete": "street-address", "maxlength": "255"}
    ),
}
CONTACT_LABELS = {
    "social_name": "Nome social",
    "postal_code": "CEP",
    "address": "Endereço",
    "cns": "CNS (Cartão Nacional de Saúde)",
    "municipality_code": "Município",
    "ethnicity_code": "Etnia indígena",
    "birth_country_code": "País de nascimento",
}
CONTACT_HELP_TEXTS = {
    "mother_name": "Se desconhecida, informe SEM INFORMAÇÃO.",
    "municipality_code": "Escolha na lista; a UF é preenchida pelo município.",
    "ethnicity_code": "Obrigatória quando raça/cor for indígena.",
    "birth_country_code": "Obrigatório para naturalizados e estrangeiros.",
}


class MunicipalityField(forms.CharField):
    """Mostra 'Nome/UF' e grava o codigo IBGE; aceita tambem o codigo de 7 digitos."""

    def widget_attrs(self, widget):
        return {}  # o maxlength=7 do model cortaria o texto 'Nome/UF' digitado

    def prepare_value(self, value):
        return sus_tables.municipality_label(value) or value

    def to_python(self, value):
        value = super().to_python(value)
        if not value or value.isdigit():
            return value
        code = sus_tables.municipality_code_for(value)
        if code is None:
            raise ValidationError("Escolha um município da lista.")
        return code


def setup_sus_fields(form):
    """Opcoes de etnia e pais vindas das tabelas oficiais."""
    form.fields["ethnicity_code"].widget.choices = sus_tables.choices("etnias")
    form.fields["birth_country_code"].widget.choices = sus_tables.choices("paises")
    form.sus_fields = [form[name] for name in SUS_FIELDS]


class PatientForm(forms.ModelForm):
    confirm_new = forms.BooleanField(
        label="Conferi os possíveis cadastros existentes e este é outro paciente",
        required=False,
    )

    class Meta:
        model = Patient
        fields = [
            "identifier_type",
            "identifier",
            "full_name",
            "birth_date",
            "sex",
            *CONTACT_FIELDS,
        ]
        widgets = {
            "identifier_type": forms.Select(attrs={"class": "select"}),
            "identifier": forms.TextInput(
                attrs={"class": "input", "autocomplete": "off", "maxlength": "64"}
            ),
            "full_name": forms.TextInput(
                attrs={"class": "input", "autocomplete": "name", "maxlength": "255"}
            ),
            "birth_date": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "sex": forms.Select(attrs={"class": "select"}),
            "phone": forms.TextInput(
                attrs={"class": "input", "autocomplete": "tel", "maxlength": "32"}
            ),
            "email": forms.EmailInput(attrs={"class": "input", "autocomplete": "email"}),
            **CONTACT_WIDGETS,
        }
        labels = {
            **CONTACT_LABELS,
            "identifier_type": "Tipo de identificador",
            "identifier": "CPF, CNS ou identificador",
            "full_name": "Nome completo",
            "birth_date": "Data de nascimento",
            "sex": "Sexo",
            "phone": "Telefone",
            "email": "E-mail",
        }
        help_texts = CONTACT_HELP_TEXTS
        field_classes = {"municipality_code": MunicipalityField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setup_sus_fields(self)
        # Exigidos na producao SUS (BPA/AIH); so no cadastro novo, para nao travar
        # a atualizacao de pacientes antigos ainda sem esses dados.
        for name in ("mother_name", "municipality_code"):
            self.fields[name].required = True

    def clean(self):
        cleaned_data = super().clean()
        is_cns = cleaned_data.get("identifier_type") == Patient.IdentifierType.CNS
        if not is_cns and not cleaned_data.get("cns"):
            self.add_error("cns", "Informe o CNS do paciente.")
        return cleaned_data


class PatientContactForm(forms.ModelForm):
    """Atualizacao cadastral sem alterar identificacao canonica (regularizacao depende de G02)."""

    class Meta:
        model = Patient
        fields = CONTACT_FIELDS
        widgets = {
            **CONTACT_WIDGETS,
            "phone": forms.TextInput(
                attrs={"class": "input", "autocomplete": "tel", "maxlength": "32"}
            ),
            "email": forms.EmailInput(attrs={"class": "input", "autocomplete": "email"}),
        }
        labels = {**CONTACT_LABELS, "phone": "Telefone", "email": "E-mail"}
        help_texts = CONTACT_HELP_TEXTS
        field_classes = {"municipality_code": MunicipalityField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setup_sus_fields(self)


class EncounterForm(forms.ModelForm):
    class Meta:
        model = Encounter
        fields = ["encounter_type", "started_at", "location", "reason"]
        widgets = {
            "encounter_type": forms.Select(attrs={"class": "select"}),
            "started_at": forms.DateTimeInput(
                attrs={"class": "input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "location": forms.TextInput(
                attrs={"class": "input", "maxlength": "160", "autocomplete": "off"}
            ),
            "reason": forms.Textarea(attrs={"class": "textarea", "rows": "4", "maxlength": "2000"}),
        }
        labels = {
            "encounter_type": "Tipo de encontro",
            "started_at": "Início do atendimento",
            "location": "Local",
            "reason": "Motivo do atendimento",
        }
        help_texts = {
            "reason": "Registre apenas o contexto necessário para identificar o encontro.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["started_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        if not self.is_bound and self.instance._state.adding:
            self.fields["started_at"].initial = timezone.localtime().replace(
                second=0,
                microsecond=0,
            )


class ClinicalEvolutionForm(forms.ModelForm):
    class Meta:
        model = ClinicalEvolution
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": "10",
                    "autocomplete": "off",
                    "spellcheck": "true",
                }
            )
        }
        labels = {"content": "Evolução clínica"}
        help_texts = {
            "content": (
                "Após salvar, o conteúdo não poderá ser alterado. Correções devem ser "
                "registradas como adendo."
            )
        }


class ClinicalEvolutionAmendmentForm(forms.Form):
    amendment_reason = forms.CharField(
        max_length=255,
        label="Motivo do adendo",
        widget=forms.TextInput(attrs={"class": "input", "maxlength": "255", "autocomplete": "off"}),
    )
    content = forms.CharField(
        label="Conteúdo do adendo",
        widget=forms.Textarea(
            attrs={
                "class": "textarea",
                "rows": "10",
                "autocomplete": "off",
                "spellcheck": "true",
            }
        ),
    )

    def clean_amendment_reason(self):
        reason = " ".join((self.cleaned_data.get("amendment_reason") or "").split())
        if not reason:
            raise forms.ValidationError("Informe o motivo do adendo.")
        return reason

    def clean_content(self):
        content = (self.cleaned_data.get("content") or "").strip()
        if not content:
            raise forms.ValidationError("Informe o conteúdo do adendo.")
        return content


class ProblemForm(forms.ModelForm):
    class Meta:
        model = ProblemListEntry
        fields = [
            "description",
            "status",
            "onset_date",
            "code_system",
            "code",
            "code_version",
            "reason",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"class": "input", "maxlength": "255"}),
            "onset_date": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "code_system": forms.TextInput(attrs={"class": "input", "placeholder": "ex.: CID-10"}),
            "code": forms.TextInput(attrs={"class": "input"}),
            "code_version": forms.TextInput(attrs={"class": "input"}),
            "reason": forms.TextInput(attrs={"class": "input", "maxlength": "255"}),
        }
        labels = {
            "description": "Problema (texto livre)",
            "status": "Situação",
            "onset_date": "Início (opcional)",
            "code_system": "Sistema de código (opcional)",
            "code": "Código (opcional)",
            "code_version": "Versão do sistema de código",
            "reason": "Motivo da revisão",
        }
