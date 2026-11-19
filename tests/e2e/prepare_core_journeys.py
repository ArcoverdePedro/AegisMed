#!/usr/bin/env python3
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

ADMIN_USERNAME = "ci-e2e-admin"
ADMIN_PASSWORD = "ci-e2e-admin-password"


def configure_user(username, password, *, role, is_staff=False, is_superuser=False):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username)
    user.email = f"{username}@example.invalid"
    user.nivel_permissao = role
    user.is_active = True
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.set_password(password)
    user.save()
    return user


def main():
    configure_user(ADMIN_USERNAME, ADMIN_PASSWORD, role="ADM", is_staff=True, is_superuser=True)
    print("Fixture E2E pronta:", ADMIN_USERNAME)


if __name__ == "__main__":
    main()
