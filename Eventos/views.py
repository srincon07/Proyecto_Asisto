import io
import qrcode
import json
from email.mime.image import MIMEImage
from django.views.decorators.csrf import csrf_exempt
import csv
import uuid
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from Eventos.models import (
    ActividadProgramada,
    RegistroAsistencia,
)
from PersonasApp.models import Persona, Rol, Discapacidad, PersonaCargo
from EstructuraApp.models import (
    Objetivo,
    Cargo,
)
from PersonasApp.decorators import requerir_rol_organizador, requerir_rol_administrador
from .forms import (
    ActividadProgramadaForm,
    CargaMasivaAsistentesForm,
)  # Formularios creados con ModelForm


@login_required
@requerir_rol_organizador
def programar_actividad(request, pk=None):
    instancia = get_object_or_404(ActividadProgramada, pk=pk) if pk else None
    titulo = "Editar Actividad" if pk else "Programar Actividad"
    cargue_masivo = (
        True if pk else False
    )  # Solo mostramos la opción de cargue masivo al editar una actividad ya creada

    if request.method == "POST":
        form = ActividadProgramadaForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(
                request, "La actividad se ha registrado correctamente en la agenda."
            )
            return redirect("Eventos:lista_eventos")
    else:
        form = ActividadProgramadaForm(instance=instancia)

    # Objetivos necesarios para el paso 1 del formulario
    objetivos = Objetivo.objects.all().order_by("nombre_objetivo")

    context = {
        "form": form,
        "titulo": titulo,
        "objetivos": objetivos,
        "evento": instancia,
        "cargue_masivo": cargue_masivo,
    }
    return render(request, "Eventos/programar_actividad.html", context)

@login_required
@requerir_rol_organizador
# @permission_required(('Eventos.view_actividadprogramada'), raise_exception=True)
def lista_eventos(request):
    actividades = ActividadProgramada.objects.select_related(
        "id_tipo_actividad", "id_responsable"
    ).order_by("fecha_hora_inicio")
    ahora = timezone.now()

    for act in actividades:
        url_portal = request.build_absolute_uri(
            reverse("Eventos:auto_registro_asistencia", args=[act.id])
        )

        # CASO 1: PROGRAMADA (A futuro)
        if ahora < act.fecha_hora_inicio:
            act.estado_txt = "PROGRAMADA"
            act.badge_class = "bg-primary"
            act.fila_class = ""

            if act.requiere_preregistro:
                # Fila 1: Requiere preregistro previo (Permite registro anticipado en ventana de tiempo)
                cierre_preregistro = act.fecha_hora_inicio - timedelta(
                    minutes=act.minutos_anticipacion_cierre
                )
                if ahora <= cierre_preregistro:
                    act.asistencia_url = url_portal
                    act.aux_btn_txt = "Preregistro"
                else:
                    act.asistencia_url = ""  # Ventana cerrada
            else:
                # CORRECCIÓN Fila 2: NO requiere preregistro -> NO permite registros anticipados. URL vacía.
                act.asistencia_url = ""

        # CASO 2: EN CURSO (Sucediendo ahora)
        elif act.fecha_hora_inicio <= ahora <= act.fecha_hora_fin:
            act.estado_txt = "EN CURSO"
            act.badge_class = "bg-success pulse-success"
            act.fila_class = "table-success"

            # Filas 3 y 4: En curso siempre habilita la URL para validación en vivo
            act.asistencia_url = url_portal
            act.aux_btn_txt = "Confirmar Asistencia"

        # CASO 3: FINALIZADA
        else:
            act.estado_txt = "FINALIZADA"
            act.badge_class = "bg-secondary opacity-50"
            act.fila_class = ""
            act.asistencia_url = ""

    return render(request, "Eventos/lista_eventos.html", {"actividades": actividades})

@login_required
@requerir_rol_organizador
def eliminar_actividad(request, pk):
    actividad = get_object_or_404(ActividadProgramada, pk=pk)
    ahora = timezone.now()

    # REGLA DE NEGOCIO (Validación en el Servidor): Bloqueo si ya inició o finalizó
    if ahora >= actividad.fecha_hora_inicio:
        messages.error(
            request, "No se puede eliminar una actividad que ya inició o finalizó."
        )
        return redirect("Eventos:lista_eventos")

    if request.method == "POST":  # Por seguridad, las eliminaciones deben ser por POST
        actividad.delete()
        messages.success(
            request, "La actividad se quitó de la agenda de manera exitosa."
        )

    return redirect("Eventos:lista_eventos")


# 2. VISTA INTERNA: Llamada desde el botón del listado de eventos para ver quién asistió
@login_required
@requerir_rol_organizador
def panel_asistentes_actividad(request, actividad_id):
    # 1. Traemos la actividad resolviendo toda la cadena de llaves foráneas hasta Organización
    actividad = get_object_or_404(
        ActividadProgramada.objects.select_related(
            "id_tipo_actividad__id_linea__id_objetivo__id_unidad__id_organizacion"
        ),
        pk=actividad_id
    )
    
    # 2. Extraer de manera segura la organización asociada a la estructura del evento
    organizacion = None
    try:
        tipo_actividad = actividad.id_tipo_actividad
        linea = tipo_actividad.id_linea
        objetivo = linea.id_objetivo
        unidad = objetivo.id_unidad
        organizacion = unidad.id_organizacion
    except AttributeError:
        # En caso de que algún eslabón intermedio sea nulo en la BD
        pass

    # 3. Traemos las asistencias con select_related optimizado para la tabla
    asistencias = (
        actividad.asistencias.all()
        .select_related("asistente")
        .order_by("-fecha_registro")
    )

    # Estadísticas para las tarjetas del panel web
    asistentes_confirmados = asistencias.filter(estado="CONFIRMADO")
    asistentes_registrados = asistencias.filter(estado="REGISTRADO")

    context = {
        "actividad": actividad,
        "organizacion": organizacion,  # <-- Nueva variable inyectada al contexto
        "asistencias": asistencias,
        "asistentes_confirmados": asistentes_confirmados,
        "asistentes_registrados": asistentes_registrados,
    }
    return render(request, "Eventos/panel_asistentes_visualizacion.html", context)


# ENDPOINT AUXILARIO: Obtener roles disponibles para el formulario
@login_required
def obtener_roles_disponibles(request):
    roles = Rol.objects.all().order_by("nombre_role")
    return JsonResponse(
        {"roles": [{"id": rol.id, "nombre": rol.nombre_role} for rol in roles]}
    )


# 1. EL PORTAL PRINCIPAL (Muestra la pantalla base)
def auto_registro_asistencia(request, actividad_id):
    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
    ahora = timezone.now()

    enlace_activo = False
    modo_formulario = "PREREGISTRO"  # Flag para personalizar el HTML

    # --- ESCENARIO A: EL EVENTO REQUIERE PRERREGISTRO ---
    if actividad.requiere_preregistro:
        limite_cierre_preregistro = actividad.fecha_hora_inicio - timezone.timedelta(
            minutes=actividad.minutos_anticipacion_cierre
        )
        evento_en_curso = (
            actividad.fecha_hora_inicio <= ahora <= actividad.fecha_hora_fin
        )

        # 1. Ventana de inscripción previa
        if ahora <= limite_cierre_preregistro:
            enlace_activo = True
            modo_formulario = "PREREGISTRO"

        # 2. Ventana de auto-confirmación en el evento en vivo
        elif evento_en_curso and not actividad.permite_qr_invertido:
            enlace_activo = True
            modo_formulario = "AUTO_CONFIRMACION"

    # --- ESCENARIO B: EL EVENTO NO REQUIERE PRERREGISTRO (REGISTRO EN VIVO) ---
    else:
        evento_en_curso = (
            actividad.fecha_hora_inicio <= ahora <= actividad.fecha_hora_fin
        )

        if evento_en_curso:
            # Validamos la restricción de tiempo limitado de escaneo si está activa
            if (
                actividad.confirmacion_asistencia_temporal
                and actividad.minutos_duracion_enlace
            ):
                limite_expiracion = actividad.fecha_hora_inicio + timezone.timedelta(
                    minutes=actividad.minutos_duracion_enlace
                )
                if ahora <= limite_expiracion:
                    enlace_activo = True
                    modo_formulario = "REGISTRO_DIRECTO"
            else:
                # Si no es temporal, está activo todo el evento
                enlace_activo = True
                modo_formulario = "REGISTRO_DIRECTO"

    # =========================================================================

    # Cargar discapacidades activas para el formulario
    discapacidades = Discapacidad.objects.filter(estado="Activo").order_by(
        "nombre_discapacidad"
    )
    # Cargar generos para el formulario
    generos = [opcion[0] for opcion in Persona.OPCIONES_GENERO]

    context = {
        "actividad": actividad,
        "discapacidades": discapacidades,
        "generos": generos,
        "enlace_activo": enlace_activo,
        "modo_formulario": modo_formulario,
    }

    return render(
        request,
        "Eventos/portal_registro_formulario.html",
        context,
    )


# 2. ENDPOINT AJAX: Evalúa el estado del documento ingresado
def verificar_asistente_ajax(request, actividad_id):
    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
    documento = request.GET.get("documento", "").strip()

    if not documento:
        return JsonResponse(
            {"status": "error", "message": "Documento requerido"}, status=400
        )

    ahora = timezone.now()
    evento_en_curso = actividad.fecha_hora_inicio <= ahora <= actividad.fecha_hora_fin

    try:
        persona = Persona.objects.get(identificacion=documento)
        registro = RegistroAsistencia.objects.filter(
            actividad=actividad, asistente=persona
        ).first()

        if registro:
            if registro.estado == "CONFIRMADO":
                return JsonResponse(
                    {
                        "status": "YA_CONFIRMADO",
                        "message": f"Hola {persona.nombres}, tu presencia ya está confirmada en este evento.",
                    }
                )

            if evento_en_curso:
                # El usuario ya está inscrito y el evento está en desarrollo -> Confirmar Asistencia con PIN
                return JsonResponse(
                    {"status": "SOLICITAR_PIN", "nombre": persona.nombres}
                )
            else:
                # El usuario ya está inscrito pero el evento es a futuro
                return JsonResponse(
                    {
                        "status": "SOLO_REGISTRADO",
                        "message": f"Hola {persona.nombres}, ya te encuentras preregistrado para esta actividad.",
                    }
                )
                
        # --- REQUERIMIENTO DE CARGOS: PERSONA EXISTE ---
        # Buscamos cargos con estado "Activo" asociados a la persona
        cargos_activos = PersonaCargo.objects.filter(persona=persona, estado="Activo").select_related("cargo")
        
        if cargos_activos.exists():
            # Regla 1: Mostrar únicamente sus cargos en estado activo
            cargos_data = [
                {"id": pc.cargo.id, "nombre": pc.cargo.nombre_cargo}  # Asegúrate de usar el atributo correcto de tu app EstructuraApp
                for pc in cargos_activos
            ]
        else:
            # Regla 2: Si existe pero no tiene cargos activos, se puebla con el Cargo ID = 1
            try:
                cargo_defecto = Cargo.objects.get(id=1)
                cargos_data = [{"id": cargo_defecto.id, "nombre": cargo_defecto.nombre_cargo}]
            except Cargo.DoesNotExist:
                cargos_data = []

        # Si la persona existe en el sistema pero NO está vinculada a esta actividad concreta:
        if evento_en_curso:
            if actividad.requiere_preregistro:
                # En curso + Requiere preregistro obligatorio -> Bloquear nuevo registro
                return JsonResponse({"status": "RECHAZAR_NUEVO_REGISTRO"})
            else:
                # En curso + Sin preregistro -> Registro libre directo en vivo
                return_status = "COMPLETAR_REGISTRO"
        else:
            # Evento PROGRAMADO: Inscripción libre previa
            return_status = "COMPLETAR_REGISTRO"

    except Persona.DoesNotExist:
        # El usuario no existe en absoluto en la base de datos
        if evento_en_curso and actividad.requiere_preregistro:
            # En curso + Requiere preregistro obligatorio -> Bloquear
            return JsonResponse({"status": "RECHAZAR_NUEVO_REGISTRO"})
        
        # --- REQUERIMIENTO DE CARGOS: PERSONA NO EXISTE ---
        # Regla 2: Al ser un registro completamente nuevo, se puebla por defecto con el Cargo ID = 1
        try:
            cargo_defecto = Cargo.objects.get(id=1)
            cargos_data = [{"id": cargo_defecto.id, "nombre": cargo_defecto.nombre_cargo}]
        except Cargo.DoesNotExist:
            cargos_data = []

        return_status = "NUEVO_REGISTRO"

    # Retorno de datos para rellenar el formulario si pasó los filtros de bloqueo
    if return_status == "COMPLETAR_REGISTRO":
        return JsonResponse(
            {
                "status": "COMPLETAR_REGISTRO",
                "nombre": persona.nombres,
                "apellido": persona.apellidos,
                "correo": persona.email,
                "telefono": persona.telefono or "",
                "organizacion_origen": persona.organizacion_origen or "",
                "genero": persona.genero or "",
                "discapacidad": persona.discapacidad.id if persona.discapacidad else "",
                "cargos": cargos_data,  # <-- Inyección de los cargos filtrados
            }
        )

    return JsonResponse({"status": "NUEVO_REGISTRO", "cargos": cargos_data})  # <-- Inyección para usuarios nuevos


# 3. PROCESAMIENTO FINAL: Guarda el formulario (Registro o Confirmación con PIN)
def procesar_asistencia_ajax(request, actividad_id):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Método no permitido"}, status=405
        )

    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
    accion = request.POST.get("accion")
    documento = request.POST.get("documento", "").strip()

    if accion == "procesar_pin":
        pin_ingresado = request.POST.get("pin_evento", "").strip()
        persona = get_object_or_404(Persona, identificacion=documento)
        registro = get_object_or_404(
            RegistroAsistencia, actividad=actividad, asistente=persona
        )

        if actividad.pin_confirmacion and pin_ingresado == actividad.pin_confirmacion:
            registro.estado = "CONFIRMADO"
            registro.fecha_confirmacion = timezone.now()
            registro.save()
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"{persona.nombres}, Su participación ha sido registrada correctamente.",
                }
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "El código PIN es incorrecto."}
            )

    elif accion == "registrar_nuevo":
        ahora = timezone.now()

        if not documento:
            return JsonResponse(
                {"status": "error", "message": "El número de documento es obligatorio."}
            )

        # =========================================================================
        # 1. EVENTOS QUE REQUIEREN PRERREGISTRO
        # =========================================================================
        if actividad.requiere_preregistro:
            # Límite donde se cierra la ventana de inscripción previa
            limite_cierre = actividad.fecha_hora_inicio - timezone.timedelta(
                minutes=actividad.minutos_anticipacion_cierre
            )

            # -----------------------------------------------------------------
            # MOMENTO A: EN VIVO (El evento ya va a iniciar o está en curso)
            # -----------------------------------------------------------------
            if ahora > limite_cierre:

                # REGLA 1.a: Si tiene Pase Digital habilitado -> Bloquear Auto-Confirmación
                if actividad.permite_qr_invertido:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "La auto-confirmación no está permitida para este evento. Debe presentar su pase digital con el operador en puerta.",
                        }
                    )

                # REGLA 1.b: Pase digital NO habilitado -> Permite auto-confirmación en vivo de inscritos
                try:
                    registro_existente = RegistroAsistencia.objects.get(
                        actividad=actividad, asistente__identificacion=documento
                    )

                    if registro_existente.estado == "CONFIRMADO":
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": f"Tu asistencia ya fue confirmada previamente a las {registro_existente.fecha_confirmacion.strftime('%H:%M')}.",
                            }
                        )

                    registro_existente.estado = "CONFIRMADO"
                    registro_existente.fecha_confirmacion = ahora
                    registro_existente.save()

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": f"¡Hola {registro_existente.asistente.nombre}! Tu asistencia ha sido confirmada correctamente.",
                        }
                    )

                except RegistroAsistencia.DoesNotExist:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "No te encuentras preregistrado en esta actividad y el periodo de inscripciones ha finalizado.",
                        }
                    )

            # -----------------------------------------------------------------
            # MOMENTO B: VENTANA DE PRERREGISTRO (Previo al inicio y cierre)
            # -----------------------------------------------------------------
            else:
                nombre = request.POST.get("nombre", "").strip()
                apellido = request.POST.get("apellido", "").strip()
                correo = request.POST.get("correo", "").strip().lower()
                telefono = request.POST.get("telefono", "").strip()
                organizacion = request.POST.get("organizacion_origen", "").strip()
                genero = request.POST.get("genero", "Masculino").strip()
                discapacidad_id = request.POST.get("discapacidad", "").strip()
                cargo_seleccionado_id = request.POST.get("cargo", "").strip()

                # Buscamos o creamos la Persona
                persona, creada = Persona.objects.get_or_create(
                    identificacion=documento,
                    defaults={
                        "nombres": nombre,
                        "apellidos": apellido,
                        "email": correo,
                        "telefono": telefono,
                        "organizacion_origen": organizacion,
                        "genero": genero,
                    },
                )

                # Si ya existía, actualizamos sus datos por si cambiaron corporativamente
                if not creada:
                    persona.nombres = nombre
                    persona.apellidos = apellido
                    persona.email = correo
                    persona.telefono = telefono
                    persona.organizacion_origen = organizacion
                    persona.genero = genero
                    # Actualizamos discapacidad si viene del formulario
                    if discapacidad_id:
                        try:
                            persona.discapacidad = Discapacidad.objects.get(
                                id=discapacidad_id
                            )
                        except Discapacidad.DoesNotExist:
                            persona.discapacidad = None
                    persona.save()

                else:
                    # Si se creó nueva persona, asignar discapacidad si fue seleccionada
                    if discapacidad_id:
                        try:
                            persona.discapacidad = Discapacidad.objects.get(
                                id=discapacidad_id
                            )
                        except Discapacidad.DoesNotExist:
                            persona.discapacidad = None
                        persona.save()

                # if creada:
                if cargo_seleccionado_id:
                    try:
                        cargo_obj = Cargo.objects.get(id=cargo_seleccionado_id)
                        # Usamos get_or_create para asegurar que si ya cuenta con la relación activa no se duplique por base de datos
                        PersonaCargo.objects.get_or_create(
                            persona=persona,
                            cargo=cargo_obj,
                            defaults={"estado": "Activo"}
                        )
                    except Cargo.DoesNotExist:
                        pass

                # Verificar si ya tiene un registro previo para evitar duplicar la inscripción
                registro_previo = RegistroAsistencia.objects.filter(
                    actividad=actividad, asistente=persona
                ).first()
                if registro_previo:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Ya te encuentras prerregistrado en esta actividad.",
                        }
                    )

                # Generación del código condicional según la regla 1.a
                token_pase = None
                if actividad.permite_qr_invertido:
                    token_pase = f"PASE-{uuid.uuid4().hex[:8].upper()}"

                # Almacenamos la inscripción
                registro = RegistroAsistencia.objects.create(
                    actividad=actividad,
                    asistente=persona,
                    estado="REGISTRADO",
                    fecha_registro=ahora,
                    codigo_pase_unico=token_pase,
                )

                # === ENVIAR CORREO ELECTRÓNICO (AGREGAR AQUÍ) ===
                # Validamos que la persona tenga un correo registrado
                if persona.email:
                    if token_pase:
                        try:
                            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                            qr.add_data(registro.codigo_pase_unico)
                            qr.make(fit=True)
                            img_qr = qr.make_image(fill_color="black", back_color="white")
                            buffer_memoria = io.BytesIO()
                            img_qr.save(buffer_memoria, format='PNG')
                            buffer_memoria.seek(0)

                            asunto = f"Tu Pase Digital - {actividad.nombre_evento}"
                            De = "Eventos Institucionales <no-reply@tuinstitucion.edu.co>"
                            Para = [persona.email]

                            # Contexto que se le pasará a la plantilla HTML
                            contexto = {
                                "persona": persona,
                                "actividad": actividad,
                                "codigo_pase": registro.codigo_pase_unico,
                            }

                            # Renderizar el HTML con las variables del contexto
                            html_content = render_to_string(
                                "Eventos/emails/email_pase_digital.html", contexto
                            )
                            # Texto alternativo plano en caso de que el gestor de correo no soporte HTML
                            text_content = strip_tags(html_content)

                            # Configuración del correo compuesto (Multi-part)
                            msg = EmailMultiAlternatives(asunto, text_content, De, Para)
                            msg.attach_alternative(html_content, "text/html")
                            
                            msg_img = MIMEImage(buffer_memoria.getvalue())
                            msg_img.add_header('Content-ID', '<qr_code>')
                            msg_img.add_header('Content-Disposition', 'inline', filename='qr_code.png')
                            msg.attach(msg_img)

                            # Enviar definitivamente
                            msg.send()

                        except Exception as email_err:
                            # Logueamos el error de correo en la consola del backend, pero permitimos que la vista termine exitosamente
                            print(f"Error crítico al enviar el correo: {str(email_err)}")
                    else:
                        asunto = f"Confirmación de Inscripción - {actividad.nombre_evento}"
                        De = "Eventos Institucionales <no-reply@tuinstitucion.edu.co>"
                        Para = [persona.email]
                        contexto = {
                            "persona": persona,
                            "actividad": actividad,
                        }
                        html_content = render_to_string(
                            "Eventos/emails/email_confirmacion_inscripcion.html", contexto
                        )
                        msg = EmailMultiAlternatives(asunto, strip_tags(html_content), De, Para)
                        msg.attach_alternative(html_content, "text/html")
                        try:
                            msg.send()
                        except Exception as email_err:
                            print(f"Error al enviar correo de confirmación: {str(email_err)}")

                msg_inscripcion = (
                    "Su participación ha sido registrada."
                )
                if token_pase:
                    msg_inscripcion = f"Su participación ha sido registrada. Su pase digital {token_pase} ha sido enviado a su correo."

                return JsonResponse({"status": "success", "message": msg_inscripcion})

        # =========================================================================
        # 2. EVENTOS SIN PRERREGISTRO (REGISTRO DIRECTO EN VIVO)
        # =========================================================================
        else:
            # Determinamos el límite de tiempo superior para admitir el registro
            if (
                actividad.confirmacion_asistencia_temporal
                and actividad.minutos_duracion_enlace
            ):
                # Caso 2.a: Enlace temporal habilitado (Inicio + Minutos de tolerancia)
                limite_expiracion = actividad.fecha_hora_inicio + timezone.timedelta(
                    minutes=actividad.minutos_duracion_enlace
                )
            else:
                # Caso 2.b: Enlace temporal NO habilitado (Hasta la hora de finalización del evento)
                limite_expiracion = actividad.fecha_hora_fin

            if ahora > limite_expiracion:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "El tiempo límite permitido para registrar asistencia en este evento ha expirado.",
                    }
                )

            # Tu lógica exacta de recolección y persistencia inmediata como CONFIRMADO
            nombre = request.POST.get("nombre", "").strip()
            apellido = request.POST.get("apellido", "").strip()
            correo = request.POST.get("correo", "").strip().lower()
            telefono = request.POST.get("telefono", "").strip()
            organizacion = request.POST.get("organizacion_origen", "").strip()
            genero = request.POST.get("genero", "Masculino").strip()
            discapacidad_id = request.POST.get("discapacidad", "").strip()
            cargo_seleccionado_id = request.POST.get("cargo", "").strip()

            persona, creada = Persona.objects.get_or_create(
                identificacion=documento,
                defaults={
                    "nombres": nombre,
                    "apellidos": apellido,
                    "email": correo,
                    "telefono": telefono,
                    "organizacion_origen": organizacion,
                    "genero": genero,
                },
            )

            # Si ya existía, actualizamos sus datos por si cambiaron corporativamente
            if not creada:
                persona.nombres = nombre
                persona.apellidos = apellido
                persona.email = correo
                persona.telefono = telefono
                persona.organizacion_origen = organizacion
                persona.genero = genero
                # Actualizamos discapacidad si viene del formulario
                if discapacidad_id:
                    try:
                        persona.discapacidad = Discapacidad.objects.get(
                            id=discapacidad_id
                        )
                    except Discapacidad.DoesNotExist:
                        persona.discapacidad = None
                persona.save()

            else:
                # Si se creó nueva persona, asignar discapacidad si fue seleccionada
                if discapacidad_id:
                    try:
                        persona.discapacidad = Discapacidad.objects.get(
                            id=discapacidad_id
                        )
                    except Discapacidad.DoesNotExist:
                        persona.discapacidad = None
                    persona.save()

            # if creada:
            if cargo_seleccionado_id:
                try:
                    cargo_obj = Cargo.objects.get(id=cargo_seleccionado_id)
                    # Usamos get_or_create para asegurar que si ya cuenta con la relación activa no se duplique por base de datos
                    PersonaCargo.objects.get_or_create(
                        persona=persona,
                        cargo=cargo_obj,
                        defaults={"estado": "Activo"}
                    )
                except Cargo.DoesNotExist:
                    pass

            registro, creado_reg = RegistroAsistencia.objects.get_or_create(
                actividad=actividad,
                asistente=persona,
                defaults={
                    "estado": "CONFIRMADO",
                    "fecha_confirmacion": ahora,
                    # "observaciones": observaciones if observaciones else None
                },
            )

            if not creado_reg and registro.estado == "CONFIRMADO":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Esta identificación ya registró su asistencia para esta actividad.",
                    }
                )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Tu asistencia ha sido registrada y confirmada exitosamente.",
                }
            )
@login_required
def interfaz_escaneo_asistencia(request, actividad_id):
    """Renderiza la pantalla de captura para el organizador de la puerta."""
    actividad = get_object_or_404(ActividadProgramada, id=actividad_id)
    return render(request, "Eventos/interfaz_escaneo.html", {"actividad": actividad})


def validar_codigo_asistencia_ajax(request, actividad_id):
    """
    Procesa el código (cédula o token único) enviado en vivo por el organizador.
    Valida vigencia horaria y cambia el estado a CONFIRMADO de inmediato.
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Método no permitido"}, status=405
        )

    actividad = get_object_or_404(ActividadProgramada, id=actividad_id)
    ahora = timezone.now()

    # Validar si todo el evento ya caducó formalmente por calendario
    if ahora < actividad.fecha_hora_inicio or ahora > actividad.fecha_hora_fin:
        return JsonResponse(
            {
                "status": "error",
                "message": "Este evento no se encuentra en curso.",
            }
        )

    try:
        data = json.loads(request.body)
        codigo_leido = data.get("codigo", "").strip()
    except Exception:
        return JsonResponse(
            {"status": "error", "message": "Datos de petición inválidos."}
        )

    if not codigo_leido:
        return JsonResponse({"status": "error", "message": "Código vacío."})

    # ESCENARIO A: El evento maneja Prerregistro (Buscamos por Pase Único QR)
    if actividad.requiere_preregistro:
        try:
            registro = RegistroAsistencia.objects.get(
                actividad=actividad, codigo_pase_unico=codigo_leido
            )

            if registro.estado == "CONFIRMADO":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Acceso ya registrado previamente para: {registro.asistente.nombres} {registro.asistente.apellidos}.",
                    }
                )

            # Cambiar estado a presencia física confirmada
            registro.estado = "CONFIRMADO"
            registro.fecha_confirmacion = ahora
            registro.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"¡Bienvenido(a)! {registro.asistente.nombres} {registro.asistente.apellidos} - Entrada Confirmada.",
                }
            )

        except RegistroAsistencia.DoesNotExist:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "El pase digital escaneado no pertenece a ningún usuario prerregistrado para este evento.",
                }
            )

    # ESCENARIO B: El evento NO requiere Prerregistro (El código leído es directamente la Cédula/Identificación)
    else:
        # Validar la restricción de tiempo de escaneo limitado si está activa
        if (
            actividad.confirmacion_asistencia_temporal
            and actividad.minutos_duracion_enlace
        ):
            limite = actividad.fecha_hora_inicio + timezone.timedelta(
                minutes=actividad.minutos_duracion_enlace
            )
            if ahora > limite:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Acceso denegado: El tiempo límite de tolerancia para el ingreso ha caducado.",
                    }
                )

        try:
            persona = Persona.objects.get(identificacion=codigo_leido)
        except Persona.DoesNotExist:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"La identificación {codigo_leido} no está registrada en la base de datos institucional.",
                }
            )

        # Buscar si ya tiene una fila de asistencia o crearla con estado CONFIRMADO
        registro, creado = RegistroAsistencia.objects.get_or_create(
            actividad=actividad,
            asistente=persona,
            defaults={"estado": "CONFIRMADO", "fecha_confirmacion": ahora},
        )

        if not creado:
            if registro.estado == "CONFIRMADO":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Esta identificación ya fue ingresada: {persona.nombre} {persona.apellido}.",
                    }
                )
            else:
                registro.estado = "CONFIRMADO"
                registro.fecha_confirmacion = ahora
                registro.save()

        return JsonResponse(
            {
                "status": "success",
                "message": f"Registro Exitoso: {persona.nombres} {persona.apellidos} ha ingresado.",
            }
        )

@login_required
@requerir_rol_organizador
def importar_asistentes_csv(request, actividad_id):
    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)

    if request.method == "POST":
        form = CargaMasivaAsistentesForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES["archivo_csv"]

            if not archivo.name.endswith(".csv"):
                messages.error(
                    request, "Error: El archivo debe tener la extensión .csv"
                )
                return redirect(request.path)

            try:
                # Leer archivo desde el flujo de memoria
                contenido = archivo.read().decode(
                    "utf-8-sig"
                )  # utf-8-sig remueve el BOM de Excel
                stream = io.StringIO(contenido)
                lector_csv = csv.DictReader(stream)

                # Validar la presencia de las columnas requeridas en el encabezado
                columnas_requeridas = {
                    "identificacion",
                    "nombres",
                    "apellidos",
                    "correo",
                    "telefono",
                    "empresa o dependencia",
                    "genero",
                }
                if not columnas_requeridas.issubset(lector_csv.fieldnames or []):
                    messages.error(
                        request,
                        "El CSV no contiene las columnas requeridas: identificacion, nombres, apellidos, correo, telefono, empresa o dependencia, genero",
                    )
                    return redirect(request.path)

                conteo_creados = 0
                conteo_inscritos = 0
                conteo_omitidos_duplicados = 0
                n_fila = 2  # Inicializador por si falla antes de entrar al bucle

                # Procesamiento seguro y transaccional
                with transaction.atomic():

                    # REQUERIMIENTO: Buscar el cargo por defecto ID 1 ANTES del bucle para optimizar queries
                    try:
                        cargo_defecto = Cargo.objects.get(id=1)
                    except Cargo.DoesNotExist:
                        messages.error(
                            request,
                            "Error crítico: El cargo predeterminado con ID 1 no existe en el sistema.",
                        )
                        return redirect(request.path)

                    for n_fila, fila in enumerate(lector_csv, start=2):
                        # Limpieza de espacios en blanco
                        doc = fila["identificacion"].strip()
                        nombre = fila["nombres"].strip()
                        apellido = fila["apellidos"].strip()
                        correo = fila["correo"].strip().lower()
                        org = fila["empresa o dependencia"].strip()
                        telefono = fila["telefono"].strip()
                        genero = fila["genero"].strip()

                        if not doc or not nombre or not apellido:
                            # Saltarse filas vacías o defectuosas de forma segura
                            continue

                        # 1. Obtener o crear la Persona inyectando el cargo_defecto en defaults
                        persona, creado = Persona.objects.get_or_create(
                            identificacion=doc,
                            defaults={
                                "nombres": nombre,
                                "apellidos": apellido,
                                "email": correo,
                                "telefono": telefono,
                                "genero": genero,
                                "organizacion_origen": org,
                            },
                        )

                        if creado:
                            conteo_creados += 1
                        else:
                            # Si ya existía la persona, actualizamos sus datos biográficos por si han cambiado corporativamente
                            persona.nombres = nombre
                            persona.apellidos = apellido
                            persona.email = correo
                            persona.telefono = telefono
                            persona.genero = genero
                            persona.organizacion_origen = org
                            persona.save()

                        # Inyección automática del Cargo ID 1 en la tabla intermedia
                        # Usamos get_or_create en PersonaCargo para evitar duplicar la relación si ya existía
                        from PersonasApp.models import (
                            PersonaCargo,
                        )  # Asegúrate de importar tu modelo intermedio

                        PersonaCargo.objects.get_or_create(
                            persona=persona,
                            cargo=cargo_defecto,
                            defaults={
                                "estado": "Activo"  # O el campo/valor por defecto que maneje tu tabla intermedia
                            },
                        )

                        # 2. Evitar duplicados en el mismo evento específico
                        registro_existente = RegistroAsistencia.objects.filter(
                            actividad=actividad, asistente=persona
                        ).exists()

                        if not registro_existente:
                            # Determinar estado en la importación masiva
                            ahora = timezone.now()
                            if (
                                ahora >= actividad.fecha_hora_inicio
                                and not actividad.requiere_preregistro
                            ):
                                estado_csv = "CONFIRMADO"
                                fecha_conf_csv = ahora
                            else:
                                estado_csv = "REGISTRADO"
                                fecha_conf_csv = None

                            # La persona no está en este evento, la vinculamos
                            RegistroAsistencia.objects.create(
                                actividad=actividad,
                                asistente=persona,
                                estado=estado_csv,
                                fecha_confirmacion=fecha_conf_csv,
                            )
                            conteo_inscritos += 1
                        else:
                            conteo_omitidos_duplicados += 1

                # Mensaje de éxito al usuario detallando las operaciones realizadas
                msg_exito = f"Procesamiento completado: Se inscribieron {conteo_inscritos} asistentes al evento."
                if conteo_creados > 0:
                    msg_exito += (
                        f" ({conteo_creados} fueron registros nuevos en el sistema)."
                    )
                if conteo_omitidos_duplicados > 0:
                    messages.info(
                        request,
                        f"Se omitieron {conteo_omitidos_duplicados} registros que ya se encontraban inscritos en esta actividad.",
                    )

                messages.success(request, msg_exito)
                return redirect("Eventos:lista_eventos")

            except Exception as e:
                messages.error(
                    request,
                    f"Ocurrió un error al procesar el archivo (Fila {n_fila}): {str(e)}",
                )
                return redirect(request.path)
    else:
        form = CargaMasivaAsistentesForm()

    return render(
        request,
        "Eventos/cargar_asistentes_masivos.html",
        {"form": form, "actividad": actividad},
    )
