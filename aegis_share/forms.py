from django import forms
from django.contrib.auth.forms import UserCreationForm
from PIL import Image, UnidentifiedImageError

from .models import CustomUser
from .utils import clear_strings


class PhoneUserCreationMixin:
    def clean_telefone(self):
        telefone = clear_strings(self.cleaned_data.get("telefone"))
        if not (10 <= len(telefone) <= 11):
            raise forms.ValidationError("Telefone invalido (DDD + 8 ou 9 digitos).")
        return telefone


class FirstUserForm(PhoneUserCreationMixin, UserCreationForm):
    email = forms.EmailField(label="Email", max_length=300, required=True)
    telefone = forms.CharField(
        label="Telefone",
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={"class": "tel"}),
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "telefone",
            "password1",
            "password2",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.telefone = self.cleaned_data["telefone"]
        user.is_staff = True
        user.is_superuser = True
        user.nivel_permissao = "ADM"
        if commit:
            user.save()
        return user


class FormUserADM(PhoneUserCreationMixin, UserCreationForm):
    email = forms.EmailField(label="Email", max_length=300, required=True)
    telefone = forms.CharField(
        label="Telefone",
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={"class": "tel"}),
    )
    nivel_permissao = forms.ChoiceField(
        label="Nivel de Permissao",
        choices=CustomUser.NIVEL_PERMISSAO_CHOICES,
        initial="CLI",
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "telefone",
            "nivel_permissao",
            "password1",
            "password2",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.telefone = self.cleaned_data["telefone"]
        user.nivel_permissao = self.cleaned_data["nivel_permissao"]
        user.is_staff = user.nivel_permissao == "ADM"
        user.is_superuser = user.nivel_permissao == "ADM"
        if commit:
            user.save()
        return user


class ClienteForm(PhoneUserCreationMixin, UserCreationForm):
    email = forms.EmailField(label="Email", max_length=300, required=True)
    telefone = forms.CharField(
        label="Telefone",
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={"class": "tel"}),
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "telefone",
            "password1",
            "password2",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.telefone = self.cleaned_data["telefone"]
        user.nivel_permissao = "CLI"
        if commit:
            user.save()
        return user


class TOTPCodeForm(forms.Form):
    code = forms.CharField(label="Codigo de autenticacao", min_length=6, max_length=20)


class FotoForm(forms.Form):
    arquivo = forms.FileField(label="Selecione a Foto", required=True)

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        if arquivo and arquivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("A foto excede o limite de 5 MB.")
        if arquivo and arquivo.content_type not in {
            "image/png",
            "image/jpeg",
            "image/webp",
        }:
            raise forms.ValidationError("Use PNG, JPEG ou WEBP.")
        # O tipo vem do navegador; confere se o conteudo e mesmo uma imagem.
        try:
            Image.open(arquivo).verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise forms.ValidationError("O arquivo enviado nao e uma imagem valida.") from exc
        arquivo.seek(0)  # verify() consome o arquivo; volta ao inicio para o uso real
        return arquivo
