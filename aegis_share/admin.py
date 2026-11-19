from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, TrackedSession, UserSecuritySettings


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "nivel_permissao", "is_staff", "is_active")
    list_filter = ("nivel_permissao", "is_staff", "is_active")
    fieldsets = (
        *UserAdmin.fieldsets,
        ("AegisShare", {"fields": ("telefone", "nivel_permissao", "foto_perfil")}),
    )
    add_fieldsets = (
        *UserAdmin.add_fieldsets,
        ("AegisShare", {"fields": ("email", "telefone", "nivel_permissao")}),
    )
    search_fields = ("username", "email", "telefone")
    ordering = ("username",)


admin.site.register(UserSecuritySettings)
admin.site.register(TrackedSession)
