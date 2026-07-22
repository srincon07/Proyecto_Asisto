from django.db import models
from django.core.validators import MinValueValidator

class Organizacion(models.Model):
    PLAN_CHOICES = [
        ('BASICO', 'Plan Básico - Solo eventos abiertos'),
        ('PRO', 'Plan Pro - Pre-registro + Evaluaciones'),
        ('ENTERPRISE', 'Plan Enterprise - Pase Digital QR + Todo'),
    ]
    nombre_organizacion = models.CharField(max_length=255, unique=True)
    nit = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    correo_electronico = models.EmailField(unique=True)
    sitio_web = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True, verbose_name="Logo de la Organización")
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='BASICO',
        verbose_name='Plan de suscripción'
    )
    
    limite_eventos_mes = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Límite de eventos por mes'
    )
    
    def __str__(self):
        return self.nombre_organizacion

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"


class Unidad(models.Model):
    # Una organización puede tener varias unidades, pero una unidad pertenece a una sola organización
    id_organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="unidades"
    )
    nombre_unidad = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre_unidad

    class Meta:
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"


class Cargo(models.Model):
    # Un cargo puede estar asociado a una o varias unidades, y una unidad puede tener varios cargos
    id_unidad = models.ForeignKey(
        Unidad, on_delete=models.PROTECT, related_name="cargos"
    )
    nombre_cargo = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nombre_cargo} - [{self.id_unidad.nombre_unidad}]"

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"


class Objetivo(models.Model):
    # Una unidad puede tener varios objetivos, pero un objetivo pertenece a una sola unidad
    id_unidad = models.ForeignKey(
        Unidad, on_delete=models.PROTECT, related_name="objetivos"
    )
    nombre_objetivo = models.CharField(max_length=255, unique=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_objetivo} - [{self.id_unidad.nombre_unidad}]"

    class Meta:
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"


class Linea(models.Model):
    # El models.PROTECT evita que borren un objetivo si tiene líneas amarradas
    id_objetivo = models.ForeignKey(
        Objetivo, on_delete=models.PROTECT, related_name="lineas"
    )
    nombre_linea = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nombre_linea} ({self.id_objetivo.nombre_objetivo})"


class TipoActividad(models.Model):
    # Definimos las opciones fijas para la modalidad
    class ModalidadChoices(models.TextChoices):
        PRESENCIAL = "Presencial", "Presencial"
        VIRTUAL = "Virtual", "Virtual"
        OTRO = "Otro", "Otro"

    id_linea = models.ForeignKey(
        Linea,
        on_delete=models.PROTECT,  # Protege si hay dependencias
        related_name="tipos_actividad",
        verbose_name="Línea de Acción",
    )
    nombre = models.CharField(max_length=255)
    modalidad = models.CharField(
        max_length=20,
        choices=ModalidadChoices.choices,
        default=ModalidadChoices.PRESENCIAL,
    )

    def __str__(self):
        return f"{self.nombre} ({self.modalidad})"
