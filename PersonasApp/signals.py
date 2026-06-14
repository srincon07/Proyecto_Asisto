# PersonasApp/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from .models import PersonaRol, Persona

@receiver(post_save, sender=PersonaRol)
@receiver(post_delete, sender=PersonaRol)
def actualizar_permisos_por_cambio_rol(sender, instance, **kwargs):
    """
    Esta señal se ejecutará SIEMPRE, tanto si guardas desde el Frontend 
    como si modificas los inlines en el Admin de Django.
    """
    # instance representa la fila de PersonaRol que se acaba de crear/borrar
    persona = instance.persona 
    
    # 1. Obtener los nombres de los roles actuales de la persona
    roles_actuales = [r.nombre_role for r in persona.roles.all()]
    
    # 2. Asegurar Grupos
    grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
    grupo_organizador, _ = Group.objects.get_or_create(name='Organizador')

    # 3. Poblar permisos si están vacíos en la BD (Blindaje de post-migración)
    todos_los_permisos = Permission.objects.all()
    if grupo_admin.permissions.count() == 0:
        permisos_admin = [
            p for p in todos_los_permisos 
            if p.content_type.app_label in ['EstructuraApp', 'Eventos'] 
            and p.content_type.model != 'organizacion'
        ]
        grupo_admin.permissions.set(permisos_admin)

    if grupo_organizador.permissions.count() == 0:
        permisos_organizador = [
            p for p in todos_los_permisos 
            if p.content_type.app_label == 'Eventos'
        ]
        grupo_organizador.permissions.set(permisos_organizador)

    # 4. Sincronizar membresías del grupo nativo de Django
    if 'Administrador' in roles_actuales:
        grupo_admin.user_set.add(persona)
    else:
        grupo_admin.user_set.remove(persona)

    if 'Organizador' in roles_actuales:
        grupo_organizador.user_set.add(persona)
    else:
        grupo_organizador.user_set.remove(persona)