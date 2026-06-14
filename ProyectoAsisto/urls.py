"""
URL configuration for ProyectoAsisto project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

# Personalización del Admin de Django
admin.site.site_header = "Panel de Administración - Asisto" # Título en la barra superior (H1)
admin.site.site_title = "Sistema Asisto"                                        # Título en la pestaña del navegador
admin.site.index_title = "Bienvenido a la gestión del Sistema Asisto"                 # Subtítulo en la página de inicio del admin

# Apunta directamente a la función de renderizado que acabamos de escribir
handler403 = 'PersonasApp.views.error_403_permiso_denegado'

urlpatterns = [
    path("admin/", admin.site.urls),
    # ESTA ES LA LÍNEA CLAVE PARA LAS RUTAS NATIVAS DE AUTENTICACIÓN
    path('accounts/', include('django.contrib.auth.urls')),
    path("personas/", include("PersonasApp.urls")),
    path("", include("EstructuraApp.urls")),
    path("eventos/", include("Eventos.urls")),
]

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
