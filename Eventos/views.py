import json
import uuid
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from Eventos.models import (
    ActividadProgramada,
    RegistroAsistencia,
)
from PersonasApp.models import Persona, Discapacidad
from EstructuraApp.models import (
    Objetivo,
)
from PersonasApp.decorators import es_miembro_grupo
from .forms import (
    ActividadProgramadaForm,
    CargaMasivaAsistentesForm,
)  # Formularios creados con ModelForm
from .services import (
    get_or_create_persona,
    enviar_notificacion_asistencia,
    procesar_csv_asistentes,
    obtener_datos_dashboard,
    procesar_verificacion_asistente,
    procesar_validacion_asistencia_pase_digital
)

@es_miembro_grupo('Administrador','Organizador')
def programar_actividad(request, pk=None):
    instancia = get_object_or_404(ActividadProgramada, pk=pk) if pk else None
    titulo = "Editar Actividad" if pk else "Programar Actividad"
    cargue_masivo = (
        True if pk else False
    )  # Solo mostramos la opción de cargue masivo al editar una actividad ya creada

    if request.method == "POST":
        form = ActividadProgramadaForm(request.POST, instance=instancia)
        if form.is_valid():
            # Validar que si el evento ya tenía asistencias, no intenten cambiar Preregistro
            if instancia and instancia.asistencias.exists():
                form.instance.requiere_preregistro = instancia.requiere_preregistro
            
            form.save()
            messages.success(request, "Actividad programada correctamente.")
            return redirect('Eventos:lista_eventos')
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
                # Requiere preregistro previo (Permite registro anticipado en ventana de tiempo)
                cierre_preregistro = act.fecha_hora_inicio - timedelta(
                    minutes=act.minutos_anticipacion_cierre
                )
                if ahora <= cierre_preregistro:
                    act.asistencia_url = url_portal
                    act.aux_btn_txt = "Preregistro"
                else:
                    act.asistencia_url = ""  # Ventana cerrada
            else:
                # NO requiere preregistro -> NO permite registros anticipados. URL vacía.
                act.asistencia_url = ""

        # CASO 2: EN CURSO (Sucediendo ahora)
        elif act.fecha_hora_inicio <= ahora <= act.fecha_hora_fin:
            act.estado_txt = "EN CURSO"
            act.badge_class = "bg-success pulse-success"
            act.fila_class = "table-success"

            # En curso siempre habilita la URL para validación en vivo
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
@es_miembro_grupo('Administrador','Organizador')
def eliminar_actividad(request, pk):
    actividad = get_object_or_404(ActividadProgramada, pk=pk)
    ahora = timezone.now()

    # REGLA DE NEGOCIO (Validación en el Servidor): Bloqueo si ya inició o finalizó
    if ahora >= actividad.fecha_hora_inicio:
        messages.error(
            request, "No se puede eliminar una actividad que ya inició o finalizó."
        )
        return redirect("Eventos:lista_eventos")
    
    if actividad.asistencias:
        messages.error(
            request, "No se puede eliminar una actividad que ya cuenta con asistentes registrados."
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
@es_miembro_grupo('Administrador','Organizador')
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
        "organizacion": organizacion,
        "asistencias": asistencias,
        "asistentes_confirmados": asistentes_confirmados,
        "asistentes_registrados": asistentes_registrados,
    }
    return render(request, "Eventos/panel_asistentes_visualizacion.html", context)


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
class VerificarAsistenteAjaxView(View):
    """
    CBV para evaluar el estado del documento ingresado en el portal de registro.
    """
    def get(self, request, actividad_id):
        actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
        documento = request.GET.get("identificacion", "").strip()

        if not documento:
            return JsonResponse(
                {"status": "error", "message": "Documento requerido"}, status=400
            )

        # Delegamos la lógica al servicio
        resultado, status_code = procesar_verificacion_asistente(actividad, documento)
        
        return JsonResponse(resultado, status=status_code)


# 3. PROCESAMIENTO FINAL: Guarda el formulario (Registro o Confirmación con PIN)
@method_decorator(es_miembro_grupo('Administrador', 'Organizador'), name='dispatch')
class ProcesarAsistenciaView(View):
    def post(self, request, actividad_id):
        self.actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
        accion = request.POST.get("accion")

        if accion == "procesar_pin":
            return self._procesar_pin(request)
        elif accion == "registrar_nuevo":
            return self._procesar_registro(request)
        
        return JsonResponse({"status": "error", "message": "Acción inválida"}, status=400)

    def _procesar_pin(self, request):
        pin = request.POST.get("pin_evento", "").strip()
        doc = request.POST.get("identificacion", "").strip()
        registro = get_object_or_404(RegistroAsistencia, actividad=self.actividad, asistente__identificacion=doc)

        if self.actividad.pin_confirmacion == pin:
            registro.estado = "CONFIRMADO"
            registro.fecha_confirmacion = timezone.now()
            registro.save()
            return JsonResponse({"status": "success", "message": "Asistencia confirmada."})
        return JsonResponse({"status": "error", "message": "PIN incorrecto."}, status=400)

    def _procesar_registro(self, request):
        
        documento = request.POST.get("identificacion", "").strip()
        if not documento:
            return JsonResponse({"status": "error", "message": "El número de documento es obligatorio."}, status=400)
        
        if self.actividad.requiere_preregistro:
            return self._flujo_con_preregistro(request)
        return self._flujo_registro_directo(request)

    def _flujo_con_preregistro(self, request):
        # Obtener la persona procesada por el servicio
        persona = get_or_create_persona(request)
        ahora = timezone.now()
        
        limite_cierre = self.actividad.fecha_hora_inicio - timezone.timedelta(
            minutes=self.actividad.minutos_anticipacion_cierre
        )

        # --- MOMENTO A: En vivo (Post-cierre) ---
        if ahora > limite_cierre:
            if self.actividad.permite_qr_invertido:
                return JsonResponse({"status": "error", "message": "Auto-confirmación bloqueada. Presente su pase digital."}, status=403)
            
            try:
                registro = RegistroAsistencia.objects.get(actividad=self.actividad, asistente=persona)
                if registro.estado == "CONFIRMADO":
                    return JsonResponse({"status": "error", "message": f"Asistencia confirmada a las {registro.fecha_confirmacion.strftime('%H:%M')}"}, status=400)
                
                registro.estado = "CONFIRMADO"
                registro.fecha_confirmacion = ahora
                registro.save()
                return JsonResponse({"status": "success", "message": "¡Asistencia confirmada!"})
            except RegistroAsistencia.DoesNotExist:
                return JsonResponse({"status": "error", "message": "No está prerregistrado."}, status=404)
        # --- MOMENTO B: Ventana de Inscripción ---
        else:
            registro, creado = RegistroAsistencia.objects.get_or_create(
                actividad=self.actividad, asistente=persona,
                defaults={
                    "estado": "REGISTRADO", 
                    "fecha_registro": ahora,
                    "codigo_pase_unico": f"PASE-{uuid.uuid4().hex[:8].upper()}"
                }
            )
            if not creado:
                return JsonResponse({"status": "error", "message": "Ya se encuentra prerregistrado."}, status=400)
            
            enviar_notificacion_asistencia(persona, self.actividad, registro, es_qr=self.actividad.permite_qr_invertido)
            return JsonResponse({"status": "success", "message": "Inscripción exitosa."})
            
    def _flujo_registro_directo(self, request):
        # Obtener la persona procesada por el servicio
        persona = get_or_create_persona(request)
        ahora = timezone.now()
        
        limite_exp = self.actividad.fecha_hora_fin
        if self.actividad.confirmacion_asistencia_temporal:
            limite_exp = self.actividad.fecha_hora_inicio + timezone.timedelta(minutes=self.actividad.minutos_duracion_enlace)

        if ahora > limite_exp:
            return JsonResponse({"status": "error", "message": "Tiempo límite expirado."}, status=403)

        registro, creado = RegistroAsistencia.objects.get_or_create(
            actividad=self.actividad, asistente=persona,
            defaults={
                "estado": "CONFIRMADO", 
                "fecha_confirmacion": ahora,
                "codigo_pase_unico": f"PASE-{uuid.uuid4().hex[:8].upper()}",
                
                }
        )
        
        if not creado and registro.estado == "CONFIRMADO":
            return JsonResponse({"status": "error", "message": "Ya registró su asistencia."}, status=400)
        
        return JsonResponse({"status": "success", "message": "Asistencia registrada exitosamente."})
        

@login_required
def interfaz_escaneo_asistencia(request, actividad_id):
    """Renderiza la pantalla de captura para el organizador de la puerta."""
    actividad = get_object_or_404(ActividadProgramada, id=actividad_id)
    return render(request, "Eventos/interfaz_escaneo.html", {"actividad": actividad})

@method_decorator(es_miembro_grupo('Administrador', 'Organizador', 'Lector-Asistencia'), name='dispatch')
class ValidarAsistenciaAjaxView(View):
    """
    CBV para procesar el código (token único) enviado en vivo.
    """
    def post(self, request, actividad_id):
        actividad = get_object_or_404(ActividadProgramada, id=actividad_id)

        try:
            data = json.loads(request.body)
            codigo_leido = data.get("codigo", "").strip()
        except Exception:
            return JsonResponse(
                {"status": "error", "message": "Datos de petición inválidos."}, status=400
            )

        # Delegamos toda la lógica de negocio al servicio
        response_data, status_code = procesar_validacion_asistencia_pase_digital(actividad, codigo_leido)
        
        return JsonResponse(response_data, status=status_code)

@method_decorator(es_miembro_grupo('Administrador', 'Organizador'), name='dispatch')
class CargaMasivaView(View):
    # Método para mostrar el formulario
    def get(self, request, actividad_id):
        actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
        form = CargaMasivaAsistentesForm()
        return render(request, 'Eventos/cargar_asistentes_masivos.html', {
            'form': form, 
            'actividad': actividad
        })
        
    def post(self, request, actividad_id):
        actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
        form = CargaMasivaAsistentesForm(request.POST, request.FILES)
        
        if form.is_valid():
            archivo = request.FILES['archivo_csv']
            reporte = procesar_csv_asistentes(archivo, actividad)
            
            # Feedback al usuario
            if not reporte["errores"]:
                messages.success(request, f"¡Éxito! Se importaron {reporte['exitos']} asistentes.")
            else:
                messages.warning(request, f"Importación finalizada. {reporte['exitos']} éxitos, {len(reporte['errores'])} errores.")
                
        # Si el formulario no es válido o hay errores en el CSV, volvemos a renderizar
        return render(request, 'Eventos/cargar_asistentes_masivos.html', {
            'form': form, 
            'actividad': actividad,
            'errores_csv': reporte.get("errores", []) if 'reporte' in locals() else None
        })

@login_required
@es_miembro_grupo('Administrador')
def api_indicadores(request):
    actividad_id = request.GET.get('evento_id')
    data = obtener_datos_dashboard(actividad_id)
    return JsonResponse(data, safe=False)

@login_required
@es_miembro_grupo('Administrador')
def dashboard_view(request):
    eventos = ActividadProgramada.objects.all().order_by('-fecha_hora_inicio')
    return render(request, 'Eventos/dashboard.html', {'eventos': eventos})