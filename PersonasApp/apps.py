from django.apps import AppConfig


class PersonasappConfig(AppConfig):
    name = "PersonasApp"

    def ready(self):
        import PersonasApp.signals  # Carga las señales al iniciar el servidor