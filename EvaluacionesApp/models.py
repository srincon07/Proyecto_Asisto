from django.db import models
from django.core.validators import MinValueValidator
from Eventos.models import ActividadProgramada

class Evaluacion(models.Model):
    actividad = models.OneToOneField(ActividadProgramada, on_delete=models.CASCADE, related_name='evaluacion')
    titulo = models.CharField(max_length=200, default="Encuesta de Satisfacción")
    activa = models.BooleanField(default=False)

class Pregunta(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.CharField(max_length=500)
    escala_maxima = models.PositiveIntegerField(validators=[MinValueValidator(2)], default=2) # Para definir si es 1-5 o 1-10

class OpcionRespuesta(models.Model):
    """Permite mapear un valor numérico a un texto (label)"""
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    valor = models.PositiveIntegerField() # ej: 1, 2, 3...
    label = models.CharField(max_length=100) # ej: "Muy insatisfecho"
    
class RespuestaAnonima(models.Model):
    """
    Almacena las respuestas de los asistentes sin vincularlas a una persona.
    """
    pregunta = models.ForeignKey(
        Pregunta, 
        on_delete=models.CASCADE, 
        related_name='respuestas'
    )
    opcion = models.ForeignKey(OpcionRespuesta, on_delete=models.PROTECT)
    fecha_respuesta = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha y hora de respuesta"
    )

    class Meta:
        verbose_name = "Respuesta Anónima"
        verbose_name_plural = "Respuestas Anónimas"

    def __str__(self):
        return f"Respuesta a Pregunta ID {self.pregunta.id} - Valor: {self.valor}"
    
    
class ComentarioAnonimo(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='comentarios')
    texto = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)