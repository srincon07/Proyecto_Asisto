from django.contrib.auth.decorators import user_passes_test

def es_miembro_grupo(*group_names):
    """
    Permite validar si el usuario pertenece al menos a uno de los grupos especificados
    o si es superusuario.
    Ejemplo de uso: 
    @es_miembro_grupo('Organizador')
    @es_miembro_grupo('Administrador', 'Organizador')
    """
    def check_groups(u):
        if not u.is_authenticated:
            return False
        return u.is_superuser or u.groups.filter(name__in=group_names).exists()
        
    return user_passes_test(check_groups)