from django.contrib import admin
from .models import (
    ActividadProgramada,
    RegistroAsistencia,
)


@admin.register(ActividadProgramada)
class ActividadProgramadaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_evento",
        "id_responsable",
        "fecha_hora_inicio",
        "fecha_hora_fin",
    )
    search_fields = ("nombre_evento", "id_responsable__nombres_completos")
    list_filter = ("id_responsable", "fecha_hora_inicio")


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = (
        "actividad",
        "asistente",
        "fecha_registro",
        "fecha_confirmacion",
        "codigo_pase_unico",
    )
    search_fields = (
        "actividad__nombre_evento",
        "asistente__nombres",
        "asistente__apellidos",
        "asistente__email",
    )
    list_filter = ("actividad", "fecha_registro")
