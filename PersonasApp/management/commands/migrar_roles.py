from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from PersonasApp.models import Rol, Persona

class Command(BaseCommand):
    help = 'Migra los roles personalizados de la BD a los grupos de Django'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando migración de roles a grupos...")

        # 1. Crear grupos basados en los roles existentes
        roles_bd = Rol.objects.all()
        for rol in roles_bd:
            group, created = Group.objects.get_or_create(name=rol.nombre_role)
            if created:
                self.stdout.write(f"Grupo '{rol.nombre_role}' creado.")

            # 2. Asignar usuarios al grupo
            personas = Persona.objects.filter(roles=rol)
            for persona in personas:
                persona.groups.add(group)
            
            self.stdout.write(f"Se asignaron {personas.count()} personas al grupo '{rol.nombre_role}'.")

        self.stdout.write(self.style.SUCCESS('Migración finalizada con éxito.'))