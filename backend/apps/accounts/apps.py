from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"

    def ready(self) -> None:
        # Connects the login and logout signal receivers.
        from apps.accounts import sessions  # noqa: F401
