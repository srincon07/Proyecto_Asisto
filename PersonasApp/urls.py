from django.urls import path
from . import views

app_name = "PersonasApp"

urlpatterns = [
    path("lista/", views.lista_personas, name="lista_personas"),
    path("persona/nuevo/", views.registrar_editar_persona, name="crear_persona"),
    path(
        "persona/editar/<int:pk>/",
        views.registrar_editar_persona,
        name="editar_persona",
    ),
    path("persona/eliminar/<int:pk>/", views.eliminar_persona, name="eliminar_persona"),
]
