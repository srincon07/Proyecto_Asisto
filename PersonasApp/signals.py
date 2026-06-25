# PersonasApp/signals.py
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import Persona

@receiver(m2m_changed, sender=Persona.groups.through)
def actualizar_is_staff_por_grupo(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Se ejecuta cuando se añaden o eliminan grupos de una Persona.
    'instance' es la persona afectada.
    'action' indica qué sucedió ('post_add', 'post_remove', 'post_clear').
    """
    
    # Solo procesamos si la acción implica cambios en la relación
    if action in ['post_add', 'post_remove', 'post_clear']:
        
        # Obtenemos el grupo "Administrador"
        grupo_admin = Group.objects.filter(name='Administrador').first()
        
        if grupo_admin:
            # Verificamos si la persona pertenece al grupo Administrador
            es_admin = instance.groups.filter(name='Administrador').exists()
            
            # Si el estado de is_staff no coincide con la membresía, actualizamos
            if instance.is_staff != es_admin:
                instance.is_staff = es_admin
                instance.save(update_fields=['is_staff'])