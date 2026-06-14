from django.urls import path
from . import views

app_name = "EstructuraApp"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    # Rutas para Objetivos y Líneas
    path("gestion/", views.gestionar_estructura, name="gestion_estructura"),
    path(
        "gestion/editar/<str:edit_tipo>/<int:pk>/",
        views.gestionar_estructura,
        name="editar_estructura",
    ),
    path(
        "gestion/eliminar/<str:edit_tipo>/<int:pk>/",
        views.eliminar_estructura,
        name="eliminar_estructura",
    ),
    # Rutas para Tipos de Actividad
    path("tipos/", views.gestionar_tipos, name="gestionar_tipos"),
    path("tipos/editar/<int:pk>/", views.gestionar_tipos, name="editar_tipo"),
    path("tipos/eliminar/<int:pk>/", views.eliminar_tipo, name="eliminar_tipo"),
    # Endpoint de datos jerárquicos
    path("api/jerarquia/", views.api_get_jerarquia, name="api_get_jerarquia"),
]
