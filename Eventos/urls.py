from django.urls import path
from . import views

app_name = "Eventos"

urlpatterns = [
    # Rutas para Actividades Programadas
    path("actividad/programar/", views.programar_actividad, name="programar_actividad"),
    path(
        "actividad/editar/<int:pk>/", views.programar_actividad, name="editar_actividad"
    ),
    path("agenda/", views.lista_eventos, name="lista_eventos"),
    path(
        "actividad/eliminar/<int:pk>/",
        views.eliminar_actividad,
        name="eliminar_actividad",
    ),
    # Ruta que apunta el QR / Enlace de autogestión
    path(
        "actividad/<int:actividad_id>/unirse/",
        views.auto_registro_asistencia,
        name="auto_registro_asistencia",
    ),
    # Ruta que apunta el botón de visualización del organizador
    path(
        "actividad/<int:actividad_id>/asistentes/",
        views.panel_asistentes_actividad,
        name="panel_asistentes_actividad",
    ),
    path(
        "actividad/<int:actividad_id>/verificar/",
        views.verificar_asistente_ajax,
        name="verificar_asistente_ajax",
    ),
    path(
        "actividad/<int:actividad_id>/procesar/",
        views.procesar_asistencia_ajax,
        name="procesar_asistencia_ajax",
    ),
    path(
        "actividad/<int:actividad_id>/escanear/",
        views.interfaz_escaneo_asistencia,
        name="interfaz_escaneo_asistencia",
    ),
    path(
        "actividad/<int:actividad_id>/validar-codigo-ajax/",
        views.validar_codigo_asistencia_ajax,
        name="validar_codigo_asistencia_ajax",
    ),
    path(
        "cargue_masivo/<int:actividad_id>/",
        views.importar_asistentes_csv,
        name="importar_asistentes_csv",
    ),
    path(
        "roles/disponibles/",
        views.obtener_roles_disponibles,
        name="obtener_roles_disponibles",
    ),
]
