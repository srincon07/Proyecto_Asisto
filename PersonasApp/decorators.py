from django.contrib.auth.decorators import user_passes_test

def es_miembro_grupo(group_name):
    return user_passes_test(lambda u: u.groups.filter(name=group_name).exists() or u.is_superuser)

# Uso en views.py:
# @es_miembro_grupo('Administrador')
# def lista_personas(request): ...