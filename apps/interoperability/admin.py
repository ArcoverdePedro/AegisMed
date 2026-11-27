from django import forms
from django.contrib import admin

from aegis_med.models import CustomUser
from apps.clinical.pep.permissions import is_internal_professional

from .models import LaboratorySource, RndsSubmission


class LaboratorySourceForm(forms.ModelForm):
    class Meta:
        model = LaboratorySource
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["operators"].queryset = CustomUser.objects.filter(
            nivel_permissao__in=["ADM", "FUNC"]
        )


@admin.register(LaboratorySource)
class LaboratorySourceAdmin(admin.ModelAdmin):
    form = LaboratorySourceForm
    list_display = ["code", "active"]
    list_filter = ["active"]
    filter_horizontal = ["operators"]

    def has_view_permission(self, request, obj=None):
        return is_internal_professional(request.user) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return is_internal_professional(request.user) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return is_internal_professional(request.user) and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return is_internal_professional(request.user) and super().has_delete_permission(
            request, obj
        )


@admin.register(RndsSubmission)
class RndsSubmissionAdmin(admin.ModelAdmin):
    """Somente leitura e só metadados: nenhum dado do paciente nem do resultado aparece."""

    list_display = ["created_at", "status", "environment", "attempts", "rnds_id", "detail"]
    list_filter = ["status", "environment"]
    list_per_page = 50
    fields = [
        "id",
        "status",
        "environment",
        "detail",
        "rnds_id",
        "attempts",
        "document_key",
        "created_at",
        "updated_at",
        "sent_at",
    ]
    readonly_fields = fields

    def has_view_permission(self, request, obj=None):
        return is_internal_professional(request.user) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
