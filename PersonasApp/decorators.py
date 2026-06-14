from django.core.exceptions import PermissionDenied

def requerir_rol_administrador(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        # request.user tendrá acceso si es superusuario o tiene el rol Administrador
        if request.user.is_authenticated and request.user.es_administrador:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied # Lanza un error 403
    return _wrapped_view_func


def requerir_rol_organizador(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        # request.user tendrá acceso si tiene el rol Organizador
        if request.user.is_authenticated and request.user.es_organizador:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied # Lanza un error 403
    return _wrapped_view_func