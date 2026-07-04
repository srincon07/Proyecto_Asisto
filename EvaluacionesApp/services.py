from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse

def send_mail_evaluacion(request, registro):
    actividad = registro.actividad
    
    # Construimos la URL absoluta (ajusta 'tu-dominio.com' según tu configuración)
    path = reverse('EvaluacionesApp:responder_evaluacion', kwargs={
        'actividad_id': actividad.id, 
        'token_asistencia': registro.codigo_pase_unico
    })
    url_evaluacion = request.build_absolute_uri(path)

    subject = f"Tu opinión sobre {actividad.nombre_evento}"
    html_content = render_to_string('EvaluacionesApp/email_invitacion_evaluacion.html', {
        'registro': registro,
        'actividad': actividad,
        'url_evaluacion': url_evaluacion
    })
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        'tu_correo_de_sistema@dominio.com', # Cambia esto por tu remitente
        [registro.asistente.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()