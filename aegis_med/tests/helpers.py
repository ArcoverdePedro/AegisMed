from aegis_med.models import CustomUser


def make_user(username, *, role="CLI", password="StrongTestPass123!"):
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
        nivel_permissao=role,
    )
