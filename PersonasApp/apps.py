from django.apps import AppConfig


class PersonasappConfig(AppConfig):
    name = "PersonasApp"
    
    def ready(self):
        import PersonasApp.signals  # Esto activa la señal al iniciar Django