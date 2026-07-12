from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from PersonasApp.decorators import es_miembro_grupo
from Eventos.models import ActividadProgramada, RegistroAsistencia
from .models import Evaluacion, Pregunta, OpcionRespuesta, RespuestaAnonima, ComentarioAnonimo
from .forms import EvaluacionForm, PreguntaFormSet, OpcionFormSet
from .services import send_mail_evaluacion


@login_required
@es_miembro_grupo('Organizador')
def configurar_evaluacion(request, actividad_id):
    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
    # Obtenemos o creamos la evaluación ligada a la actividad
    evaluacion, _ = Evaluacion.objects.get_or_create(actividad=actividad)

    if request.method == "POST":
        form = EvaluacionForm(request.POST, instance=evaluacion)
        formset = PreguntaFormSet(request.POST, instance=evaluacion)
        
        if form.is_valid() and formset.is_valid():        
            form.save()
              
            # 1. Validación: Bloquear borrado de preguntas con respuestas
            for form_del in formset.deleted_forms:
                pregunta = form_del.instance
                # Solo validamos si existe en BD (tiene pk) para evitar ValueError
                if pregunta.pk and pregunta.respuestas.exists():
                    messages.error(request, f"No puedes eliminar la pregunta '{pregunta.texto}' porque ya tiene respuestas registradas.")
                    return redirect('EvaluacionesApp:configurar_evaluacion', actividad_id=actividad_id)

            # 2. Validación: Bloquear cambio de escala_maxima si hay respuestas
            # Esto recorre los formularios que NO están marcados para borrado
            for f in formset:
                if not f.cleaned_data.get('DELETE', False): # Solo si no se está eliminando
                    pregunta = f.instance
                    if pregunta.pk:
                        if 'escala_maxima' in f.changed_data:
                            if pregunta.respuestas.exists():
                                messages.error(request, f"No puedes cambiar la escala de '{pregunta.texto}' porque ya tiene respuestas.")
                                return redirect('EvaluacionesApp:configurar_evaluacion', actividad_id=actividad_id)
                        
                        if not pregunta.opciones.exists():
                            messages.error(request, f"La pregunta '{pregunta.texto}' no tiene opciones de respuesta confirmadas. Por favor, configura las opciones antes de guardar.")
                            return redirect('EvaluacionesApp:configurar_evaluacion', actividad_id=actividad_id)
            
            formset.save()
            messages.success(request, "Evaluación actualizada exitosamente.")
            return redirect('Eventos:lista_eventos')
        else:
            # CAPTURA DE ERRORES: Si form o formset no son válidos
            # Esto captura errores de validación como MinValueValidator
            for error in form.non_field_errors():
                messages.error(request, str(error))
            for f in formset:
                for field in f:
                    for error in field.errors:
                        messages.error(request, f"Error en '{f.instance.texto if f.instance.pk else 'Nueva pregunta'}': {error}")
    else:
        form = EvaluacionForm(instance=evaluacion)
        formset = PreguntaFormSet(instance=evaluacion)

    return render(request, 'EvaluacionesApp/configurar_evaluacion.html', {
        'form': form,
        'formset': formset,
        'actividad': actividad
    })
    
@transaction.atomic
def procesar_evaluacion(request, actividad_id, token_asistencia):
    # 1. Validar el derecho a voto
    registro = get_object_or_404(RegistroAsistencia, codigo_pase_unico=token_asistencia, actividad_id=actividad_id)
    evaluacion = registro.actividad.evaluacion
    
    if registro.evaluacion_completada:
        return HttpResponse("Ya has participado en esta evaluación.")

    # 2. Guardar respuestas de forma masiva
    for key, value in request.POST.items():
        if key.startswith('pregunta_'):
            pregunta_id = key.split('_')[1]
            
            # NUEVO: Buscamos la instancia de la opción en lugar de guardar el valor crudo
            try:
                opcion = OpcionRespuesta.objects.get(
                    pregunta_id=pregunta_id, 
                    valor=value
                )
                
                # Guardamos la relación con la opción
                RespuestaAnonima.objects.create(
                    pregunta_id=pregunta_id,
                    opcion=opcion  # Aquí pasamos la instancia de OpcionRespuesta
                )
            except OpcionRespuesta.DoesNotExist:
                # Esto es seguridad extra por si alguien envía valores hackeados
                continue
            
    # NUEVO: Guardar comentario si existe
    comentario_texto = request.POST.get('comentarios', '').strip()
    if comentario_texto:
        ComentarioAnonimo.objects.create(
            evaluacion=evaluacion,
            texto=comentario_texto
        )

    # 3. Marcar como completado
    registro.evaluacion_completada = True
    registro.save()
    
    return redirect('EvaluacionesApp:agradecimiento')
    
@login_required
@es_miembro_grupo('Organizador')
def configurar_opciones(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, pk=pregunta_id)
    
    # Sincronización automática: Reducir si excede la escala
    excedentes = pregunta.opciones.filter(valor__gt=pregunta.escala_maxima)
    if excedentes.exists():
        excedentes.delete()
        
    # Lógica de sincronización: Asegurar que existan objetos para el formset
    actuales = pregunta.opciones.count()
    if actuales < pregunta.escala_maxima:
        for i in range(actuales + 1, pregunta.escala_maxima + 1):
            # Creamos instancias temporales para que el formset las renderice
            OpcionRespuesta.objects.get_or_create(pregunta=pregunta, valor=i, defaults={'label': f'Nivel {i}'})
    
    if request.method == "POST":
        formset = OpcionFormSet(request.POST, instance=pregunta, queryset=pregunta.opciones.all().order_by('valor'))
        
        if formset.is_valid():
            
            # Verificar si alguna opción que se intenta borrar ya tiene respuestas
            for form in formset.deleted_forms:
                opcion = form.instance
                if RespuestaAnonima.objects.filter(pregunta=pregunta, valor=opcion.valor).exists():
                    messages.error(request, f"No puedes eliminar la opción '{opcion.label}' porque ya tiene respuestas registradas.")
                    return redirect('EvaluacionesApp:configurar_opciones', pregunta_id=pregunta.id)
                
            formset.save()
            
            messages.success(request, f"Opciones guardadas para: {pregunta.texto}")
            return redirect('EvaluacionesApp:configurar_evaluacion', actividad_id=pregunta.evaluacion.actividad.id)
    else:
        formset = OpcionFormSet(instance=pregunta, queryset=pregunta.opciones.all().order_by('valor'))

    return render(request, 'EvaluacionesApp/configurar_opciones.html', {
        'formset': formset,
        'pregunta': pregunta
    })
    
@login_required
@es_miembro_grupo('Organizador')
def gestionar_evaluacion(request, actividad_id):
    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
    
    # Validar si tiene evaluación y está habilitada (según tu modelo)
    evaluacion = getattr(actividad, 'evaluacion', None)
    
    if not evaluacion or not evaluacion.activa:
        messages.error(request, "La actividad no tiene una evaluación activa configurada.")
        return redirect('Eventos:lista_eventos')

    # Filtrar solo asistentes confirmados
    asistentes = actividad.asistencias.filter(estado='CONFIRMADO')

    if request.method == "POST":
        enviados = 0
        for registro in asistentes:
            try:
                send_mail_evaluacion(request, registro)
                enviados += 1
            except Exception as e:
                print(f"Error enviando a {registro.asistente.email}: {e}")
                #messages.error(request, f"Error enviando a {registro.asistente.nombres}: {e}")
        messages.success(request, f"Se han enviado {enviados} invitaciones a evaluación.")
        return redirect('Eventos:lista_eventos')

    return render(request, 'EvaluacionesApp/gestionar_envio.html', {'actividad': actividad, 'asistentes': asistentes})

def mostrar_evaluacion(request, actividad_id, token_asistencia):
    # Validamos que el registro pertenezca a la actividad y no haya votado aún
    registro = get_object_or_404(
        RegistroAsistencia, 
        codigo_pase_unico=token_asistencia, 
        actividad_id=actividad_id
    )
    
    if registro.evaluacion_completada:
        return render(request, 'EvaluacionesApp/agradecimiento.html', {
            'mensaje': "Ya has respondido esta encuesta anteriormente. ¡Gracias por tu participación!"
        })

    if registro.estado != 'CONFIRMADO':
        return render(request, 'EvaluacionesApp/agradecimiento.html', {
            'mensaje': "Únicamente los asistentes confirmados pueden responder la evaluación."
        })
        
    evaluacion = get_object_or_404(Evaluacion, actividad_id=actividad_id, activa=True)

    return render(request, 'EvaluacionesApp/responder_evaluacion.html', {
        'evaluacion': evaluacion,
        'actividad': evaluacion.actividad,
        'token': token_asistencia
    })
    
def agradecimiento(request, ):
    return render(request, 'EvaluacionesApp/agradecimiento.html')


@login_required
def dashboard_evaluacion(request, actividad_id):
    actividad = get_object_or_404(ActividadProgramada, pk=actividad_id)
    evaluacion = actividad.evaluacion
    
    # KPIs Básicos
    total_asistentes = actividad.asistencias.filter(estado='CONFIRMADO').count()
    
    # Total de personas que REALMENTE respondieron
    participantes_reales = RegistroAsistencia.objects.filter(
        actividad=actividad, 
        evaluacion_completada=True
    ).count()
        
    # Análisis de preguntas
    analisis = evaluacion.preguntas.annotate(
        promedio=Avg('respuestas__opcion__valor'),
        total_respuestas=Count('respuestas')
    )
    
    # Análisis detallado: Pregunta -> Opción -> Cantidad
    detalle_respuestas = []
    for pregunta in evaluacion.preguntas.all():
        opciones_conteo = pregunta.opciones.annotate(
            conteo=Count('respuestaanonima')
        )
        detalle_respuestas.append({
            'pregunta': pregunta.texto,
            'opciones': [opc.label for opc in opciones_conteo],
            'valores': [opc.conteo for opc in opciones_conteo]
        })
        
    comentarios = evaluacion.comentarios.all().order_by('-fecha_creacion')

    return render(request, 'EvaluacionesApp/dashboard_evals.html', {
        'actividad': actividad,
        'analisis': analisis,
        'tasa_participacion': (participantes_reales / total_asistentes * 100) if total_asistentes > 0 else 0,
        'total_asistentes': total_asistentes,
        'total_evaluaciones_respuestas': participantes_reales,
        'detalle_respuestas': detalle_respuestas,
        'comentarios': comentarios,
    })