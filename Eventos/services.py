import os
import io
import qrcode
import csv
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.cache import cache
from .models import RegistroAsistencia, ActividadProgramada
from django.utils import timezone
from PersonasApp.models import Persona, Discapacidad, PersonaCargo
from EstructuraApp.models import Cargo

logger = logging.getLogger(__name__)

def get_or_create_persona(request, cargo_id_default=None):
    """
    Gestiona la creación o actualización de una Persona y su cargo.
    Devuelve la instancia de Persona.
    """
    
    # Función auxiliar interna para limpiar strings de forma segura
    def safe_get(key):
        val = request.POST.get(key)
        return str(val).strip() if val is not None else ""

    documento = safe_get("identificacion")
    
    # Si no hay documento, levantamos una excepción para que el proceso la atrape
    if not documento:
        raise ValueError("Documento no proporcionado.")
    
    # Datos básicos usando la función segura
    datos = {
        "nombres": safe_get("nombres"),
        "apellidos": safe_get("apellidos"),
        "email": safe_get("correo").lower(),
        "telefono": safe_get("telefono"),
        "organizacion_origen": safe_get("organizacion_o_dependencia"),
        "genero": safe_get("genero") or "Masculino",
    }

    # 1. Obtener o crear persona
    persona, creada = Persona.objects.get_or_create(
        identificacion=documento,
        defaults=datos
    )

    # 2. Si ya existía, actualizar campos
    if not creada:
        for attr, value in datos.items():
            setattr(persona, attr, value)

    # 3. Gestionar Discapacidad
    discapacidad_id = request.POST.get("discapacidad", "").strip()
    if discapacidad_id:
        try:
            persona.discapacidad = Discapacidad.objects.get(id=discapacidad_id)
        except Discapacidad.DoesNotExist:
            persona.discapacidad = None
    
    persona.save()

    # 4. Gestionar Cargo
    cargo_id = request.POST.get("cargo", "").strip() or cargo_id_default
    if cargo_id:
        try:
            cargo_obj = Cargo.objects.get(id=cargo_id)
            PersonaCargo.objects.get_or_create(
                persona=persona,
                cargo=cargo_obj,
                defaults={"estado": "Activo"}
            )
        except Cargo.DoesNotExist:
            pass

    return persona

def procesar_verificacion_asistente(actividad, documento):
    """
    Servicio que evalúa el estado de un documento ingresado en el portal 
    de registro, determinando si es nuevo, si debe completar datos, 
    si requiere PIN, o si está bloqueado.
    """
    ahora = timezone.now()
    evento_en_curso = actividad.fecha_hora_inicio <= ahora <= actividad.fecha_hora_fin

    try:
        persona = Persona.objects.get(identificacion=documento)
        registro = RegistroAsistencia.objects.filter(
            actividad=actividad, asistente=persona
        ).first()

        if registro:
            if registro.estado == "CONFIRMADO":
                return {
                    "status": "YA_CONFIRMADO",
                    "message": f"Hola {persona.nombres}, tu presencia ya está confirmada en este evento.",
                }, 200

            if evento_en_curso:
                return {
                    "status": "SOLICITAR_PIN", 
                    "nombre": persona.nombres
                }, 200
            else:
                return {
                    "status": "SOLO_REGISTRADO",
                    "message": f"Hola {persona.nombres}, ya te encuentras preregistrado para esta actividad.",
                }, 200
                
        # --- REQUERIMIENTO DE CARGOS: PERSONA EXISTE ---
        cargos_activos = PersonaCargo.objects.filter(persona=persona, estado="Activo").select_related("cargo")
        
        if cargos_activos.exists():
            cargos_data = [
                {"id": pc.cargo.id, "nombre": pc.cargo.nombre_cargo}
                for pc in cargos_activos
            ]
        else:
            try:
                cargo_defecto = Cargo.objects.get(id=1)
                cargos_data = [{"id": cargo_defecto.id, "nombre": cargo_defecto.nombre_cargo}]
            except Cargo.DoesNotExist:
                cargos_data = []

        if evento_en_curso:
            if actividad.requiere_preregistro:
                return {"status": "RECHAZAR_NUEVO_REGISTRO"}, 200
            else:
                return_status = "COMPLETAR_REGISTRO"
        else:
            return_status = "COMPLETAR_REGISTRO"

    except Persona.DoesNotExist:
        if evento_en_curso and actividad.requiere_preregistro:
            return {"status": "RECHAZAR_NUEVO_REGISTRO"}, 200
        
        try:
            cargo_defecto = Cargo.objects.get(id=1)
            cargos_data = [{"id": cargo_defecto.id, "nombre": cargo_defecto.nombre_cargo}]
        except Cargo.DoesNotExist:
            cargos_data = []

        return_status = "NUEVO_REGISTRO"

    # Retorno de datos para rellenar el formulario si pasó los filtros
    if return_status == "COMPLETAR_REGISTRO":
        return {
            "status": "COMPLETAR_REGISTRO",
            "nombres": persona.nombres,
            "apellidos": persona.apellidos,
            "correo": persona.email,
            "telefono": persona.telefono or "",
            "organizacion_origen": persona.organizacion_origen or "",
            "genero": persona.genero or "",
            "discapacidad": persona.discapacidad.id if persona.discapacidad else "",
            "cargos": cargos_data,
        }, 200

    return {"status": "NUEVO_REGISTRO", "cargos": cargos_data}, 200

def procesar_validacion_asistencia_pase_digital(actividad, codigo_leido):
    """
    Servicio que encapsula la lógica de validación de asistencia en vivo 
    para eventos con preregistro.
    """
    ahora = timezone.now()

    # Validar si todo el evento ya caducó formalmente por calendario
    if ahora < actividad.fecha_hora_inicio or ahora > actividad.fecha_hora_fin:
        return {"status": "error", "message": "Este evento no se encuentra en curso."}, 400

    if not codigo_leido:
        return {"status": "error", "message": "Código vacío."}, 400

    # ESCENARIO A: El evento maneja Prerregistro (Buscamos por Pase Único QR)
    if actividad.requiere_preregistro:
        try:
            registro = RegistroAsistencia.objects.get(
                actividad=actividad, codigo_pase_unico=codigo_leido
            )

            if registro.estado == "CONFIRMADO":
                nombre_completo = f"{registro.asistente.nombres} {registro.asistente.apellidos}"
                return {
                    "status": "error",
                    "message": f"Acceso ya registrado previamente para: {nombre_completo}.",
                }, 400

            # Cambiar estado a presencia física confirmada
            registro.estado = "CONFIRMADO"
            registro.fecha_confirmacion = ahora
            registro.save()

            nombre_completo = f"{registro.asistente.nombres} {registro.asistente.apellidos}"
            return {
                "status": "success",
                "message": f"¡Bienvenido(a)! {nombre_completo} - Entrada Confirmada.",
            }, 200

        except RegistroAsistencia.DoesNotExist:
            return {
                "status": "error",
                "message": "El pase digital escaneado no pertenece a ningún usuario prerregistrado para este evento.",
            }, 404

def enviar_notificacion_asistencia(persona, actividad, registro, es_qr=False):
    """Maneja el envío de correos, sea con QR o confirmación simple."""
    try:
        asunto = f"Pase Digital - {actividad.nombre_evento}" if es_qr else f"Confirmación - {actividad.nombre_evento}"
        template = "Eventos/emails/email_pase_digital.html" if es_qr else "Eventos/emails/email_confirmacion_inscripcion.html"
        
        contexto = {"persona": persona, "actividad": actividad, "codigo_pase": registro.codigo_pase_unico}
        html_content = render_to_string(template, contexto)
        
        msg = EmailMultiAlternatives(asunto, strip_tags(html_content), "no-reply@institucion.edu.co", [persona.email])
        msg.attach_alternative(html_content, "text/html")

        if es_qr:
            qr = qrcode.make(registro.codigo_pase_unico)
            buffer = io.BytesIO()
            qr.save(buffer, format='PNG')
            msg_img = MIMEImage(buffer.getvalue())
            msg_img.add_header('Content-ID', '<qr_code>')
            msg.attach(msg_img)

        msg.send()
        return True
    except Exception as e:
        logger.error(f"Error enviando correo a {persona.email}: {e}")
        return False

def procesar_csv_asistentes(archivo, actividad):
    """Procesa el CSV y crea registros de asistencia de forma atómica."""
    resultados = {"exitos": 0, "errores": []}
    
    # Validación de extensión (crítica para seguridad)
    ext = os.path.splitext(archivo.name)[1]
    if ext.lower() != '.csv':
        return {"exitos": 0, "errores": ["El archivo debe tener extensión .csv"]}
    
    # Estrategia de decodificación robusta
    try:
        # Intentamos primero con utf-8-sig
        archivo.seek(0) # Asegurar que estamos al inicio del archivo
        decoded_file = archivo.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        # Si falla, usamos latin-1 (muy común en archivos de Excel)
        archivo.seek(0)
        decoded_file = archivo.read().decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded_file))
    
    # Después de crear el reader:
    if not reader.fieldnames:
        return {"exitos": 0, "errores": ["El archivo está vacío o no tiene cabeceras válidas."]}

    # Normalizar los nombres de columnas (quitar espacios accidentales)
    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
    
    # Validación de columnas requeridas (antes de iterar)
    columnas_requeridas = {
                    "identificacion",
                    "nombres",
                    "apellidos",
                    "correo",
                    "telefono",
                    "organizacion_o_dependencia",
                    "genero",
                }
    if not columnas_requeridas.issubset(set(reader.fieldnames or [])):
        return {"exitos": 0, "errores": [f"El CSV debe contener: {columnas_requeridas}"]}
    
    try:
        with transaction.atomic():
            for i, row in enumerate(reader, start=2):
                # Asegurarnos de que las claves existan y no sean None
                doc = (row.get('identificacion') or "").strip()
                nom = (row.get('nombres') or "").strip()
                ape = (row.get('apellidos') or "").strip()
                
                # Validar que no estén en blanco (saltar fila)
                if not doc or not nom or not ape:
                    resultados["errores"].append(f"Fila {i}: Falta identificación, nombres o apellidos.")
                    continue
                
                try:
                    # Reutilizamos el servicio de creación de persona
                    # Pasamos 'row' directamente, ya que get_or_create_persona usa request.POST.get
                    class MockRequest:
                        def __init__(self, data): self.POST = data
                    
                    persona = get_or_create_persona(MockRequest(row), cargo_id_default=1)
                    
                    registro, creado = RegistroAsistencia.objects.get_or_create(
                        actividad=actividad,
                        asistente=persona,
                        defaults={"estado": "REGISTRADO"}
                    )
                    
                    resultados["exitos"] += 1
                except Exception as e:
                    logger.error(f"Error en fila {i}: {e}")
                    resultados["errores"].append(f"Fila {i}: {str(e)}")
    except Exception as e:
        logger.error(f"Error crítico en carga masiva: {e}")
        resultados["errores"].append("Error crítico procesando el archivo.")
                
    return resultados

def obtener_datos_dashboard(actividad_id=None):
    # Clave dinámica por actividad para evitar conflictos en caché
    cache_key = f'dashboard_stats_{actividad_id or "global"}'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Filtro base según se seleccione un evento o todos
        qs_asistencia = RegistroAsistencia.objects.all()
        qs_actividad = ActividadProgramada.objects.all()
        
        if actividad_id:
            qs_asistencia = qs_asistencia.filter(actividad_id=actividad_id)
            qs_actividad = qs_actividad.filter(id=actividad_id)
        
        # 1. Distribución de estados
        stats_estado = list(qs_asistencia.values('estado').annotate(cantidad=Count('id')))

        # 2. Participación por tipo de actividad
        stats_tipo = list(qs_actividad.values('id_tipo_actividad__nombre')
                          .annotate(total_asistentes=Count('asistencias')))

        # 3. Tendencia (Últimos 30 días)        
        treinta_dias_atras = timezone.now() - timezone.timedelta(days=30)

        stats_tendencia = list(
            qs_asistencia.filter(
                estado='CONFIRMADO', 
                fecha_confirmacion__gte=treinta_dias_atras
            )
            .annotate(fecha=TruncDate('fecha_confirmacion')) # Transforma a fecha usando la TZ local
            .values('fecha')
            .annotate(total=Count('id'))
            .order_by('fecha')
        )
        
        # 4. Asistencia por Género (Accediendo a través de la relación)
        stats_genero = list(qs_asistencia.values('asistente__genero')
                            .annotate(cantidad=Count('id')))

        # 5. Asistencia por Discapacidad (Accediendo a través de la relación)
        stats_discapacidad = list(qs_asistencia.values('asistente__discapacidad__nombre_discapacidad')
                                  .annotate(cantidad=Count('id')))
        
        # 6. Participación por Línea
        stats_linea = list(qs_asistencia.values(
            'actividad__id_tipo_actividad__id_linea__nombre_linea'
        ).annotate(
            total_asistentes=Count('asistente', distinct=True), # Asistentes únicos por línea
            total_participaciones=Count('id')                   # Total de veces que han participado
        ))

        # 7. Participación por Objetivo
        stats_objetivo = list(qs_asistencia.values(
            'actividad__id_tipo_actividad__id_linea__id_objetivo__nombre_objetivo'
        ).annotate(
            total_asistentes=Count('asistente', distinct=True),
            total_participaciones=Count('id')
        ))
        
        local_tz = ZoneInfo("America/Bogota") # O tu zona horaria correspondiente
        time_now = timezone.now().astimezone(local_tz)

        stats = {
            "estado": stats_estado,
            "tipo": stats_tipo,
            "tendencia": stats_tendencia,
            "genero": stats_genero,
            "discapacidad": stats_discapacidad,
            "linea": stats_linea,
            "objetivo": stats_objetivo,
            "updated_at": time_now.strftime("%H:%M:%S")
        }
        
        cache.set(cache_key, stats, 300)
    
    return stats