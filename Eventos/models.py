from django.db import models
from PersonasApp.models import Persona  # Importamos el modelo de la app de personas

from EstructuraApp.models import (
    TipoActividad,
)  # Importamos el modelo de la app de estructura


class ActividadProgramada(models.Model):
    id_tipo_actividad = models.ForeignKey(
        TipoActividad,
        on_delete=models.PROTECT,
        related_name="actividades_programadas",
        verbose_name="Tipo de Actividad",
    )
    nombre_evento = models.CharField(max_length=255)
    id_responsable = models.ForeignKey(
        Persona,
        on_delete=models.PROTECT,
        related_name="actividades_responsable",
        verbose_name="Responsable",
    )
    requiere_preregistro = models.BooleanField(
        default=False, verbose_name="Requiere Preregistro"
    )
    # Nuevo campo: Almacena los mminutos de anticipación para el cierre
    minutos_anticipacion_cierre = models.PositiveIntegerField(
        default=0,
        verbose_name="Minutos previos para cierre",
        help_text="Número de minutos antes del inicio del evento en las que se cerrará el preregistro.",
    )
    # En el modelo Actividad
    permite_qr_invertido = models.BooleanField(default=False)
    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    lugar_desarrollo = models.CharField(
        max_length=255, verbose_name="Lugar de Desarrollo"
    )
    pin_confirmacion = models.CharField(
        max_length=6, blank=True, null=True, verbose_name="PIN de Validación"
    )

    # Indica si la confirmación de asistencia es temporal (solo para eventos con pase digital)
    confirmacion_asistencia_temporal = models.BooleanField(default=False)
    minutos_duracion_enlace = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minutos que durará activo el QR desde el inicio del evento",
    )
    aplicar_evaluacion = models.BooleanField(default=False)
    

    def __str__(self):
        return f"{self.nombre_evento} - {self.fecha_hora_inicio.strftime('%Y-%m-%d %H:%M')}"


class RegistroAsistencia(models.Model):
    ESTADO_CHOICES = [
        ("REGISTRADO", "Solo Registrado"),
        ("CONFIRMADO", "Presencia Confirmada"),
    ]

    actividad = models.ForeignKey(
        ActividadProgramada, on_delete=models.CASCADE, related_name="asistencias"
    )
    asistente = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="historial_actividades"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(
        blank=True, null=True
    )  # Para auditar a qué hora reconfirmó
    estado = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default="REGISTRADO"
    )
    # En el modelo RegistroAsistencia
    codigo_pase_unico = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    evaluacion_completada = models.BooleanField(default=False)

    class Meta:
        # Evita duplicar al mismo asistente en la misma actividad
        unique_together = ("actividad", "asistente")
        verbose_name = "Control de Asistencia"
        verbose_name_plural = "Controles de Asistencia"

    def __str__(self):
        return f"{self.asistente} en {self.actividad.nombre_evento}"
