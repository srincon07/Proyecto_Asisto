from django.db import models
from django.core.validators import MinValueValidator, URLValidator
from django.core.exceptions import ValidationError

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
    
    # Data Treatment Policy Fields
    correo_tratamiento_datos = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Correo para tratamiento de datos",
        help_text="Dirección de correo para consultas sobre tratamiento de datos personales"
    )
    
    url_politica_datos = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL Política de Datos",
        help_text="Enlace a la política de privacidad y tratamiento de datos"
    )
    
    texto_consentimiento = models.TextField(
        blank=True,
        default="Al registrarme, autorizo de manera expresa, libre e informada a [nombre_organizacion] y a su proveedor tecnológico Qdata Technologies SAS (Propietario de ASISTO), para el tratamiento de mis datos personales aquí consignados, con la finalidad de gestionar mi participación en sus eventos, control de aforo, envío de memorias y evaluaciones de satisfacción. Conozco que puedo ejercer mis derechos de acceso, rectificación y supresión a través del correo [correo_tratamiento_datos].",
        verbose_name="Texto de Consentimiento",
        help_text="Texto que se mostrará para solicitar el consentimiento de tratamiento de datos"
    )
    
    def clean(self):
        """Validate that if URL is provided, it's properly formatted"""
        super().clean()
        for url in [self.sitio_web, self.url_politica_datos]:
            if url:
                try:
                    URLValidator()(url)
                except ValidationError:
                    field_name = 'sitio_web' if url == self.sitio_web else 'url_politica_datos'
                    raise ValidationError({
                        field_name: 'Please enter a valid URL format.'
                    })
    
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
