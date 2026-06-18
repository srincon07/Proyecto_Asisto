from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import ProtectedError
from .models import (
    Objetivo,
    Linea,
    TipoActividad,
)
from PersonasApp.models import Persona  # <-- Importación cruzada limpia entre Apps
from PersonasApp.decorators import requerir_rol_administrador  # Decorador personalizado para control de acceso basado en roles
from Eventos.models import (
    ActividadProgramada,
)  # <-- Importación cruzada limpia entre Apps
from .forms import (
    ObjetivoForm,
    LineaForm,
    TipoActividadForm,
)  # Formularios creados con ModelForm

@login_required
@requerir_rol_administrador
def gestionar_estructura(request, edit_tipo=None, pk=None):
    # 1. Lógica para cargar datos en caso de edición
    obj_instancia = None
    linea_instancia = None
    titulo_obj = "Nuevo objetivo"
    titulo_lin = "Nueva línea de acción"
    obj_id = None
    linea_id = None

    if edit_tipo == "obj" and pk:
        obj_instancia = get_object_or_404(Objetivo, pk=pk)
        titulo_obj = "Editar Objetivo"
        obj_id = obj_instancia.id
    elif edit_tipo == "lin" and pk:
        linea_instancia = get_object_or_404(Linea, pk=pk)
        titulo_lin = "Editar Línea"
        linea_id = linea_instancia.id

    # 2. Procesamiento de Formularios
    if request.method == "POST":
        tipo_registro = request.POST.get("tipo_registro")

        if tipo_registro == "objetivo":
            form = ObjetivoForm(request.POST, instance=obj_instancia)
            if form.is_valid():
                form.save()
                return redirect("EstructuraApp:gestion_estructura")
        elif tipo_registro == "linea":
            form = LineaForm(request.POST, instance=linea_instancia)
            if form.is_valid():
                form.save()
                return redirect("EstructuraApp:gestion_estructura")

    # 3. Preparación del contexto para la plantilla
    # Django resuelve la jerarquía nativamente gracias al prefetch_related
    objetivos = (
        Objetivo.objects.prefetch_related("lineas").all().order_by("nombre_objetivo")
    )

    context = {
        "form_obj": ObjetivoForm(instance=obj_instancia),
        "form_lin": LineaForm(instance=linea_instancia),
        "objetivos": objetivos,
        "titulo_obj": titulo_obj,
        "titulo_lin": titulo_lin,
        "obj_id": obj_id,
        "linea_id": linea_id,
    }
    return render(request, "EstructuraApp/registro_estructura.html", context)

@login_required
@requerir_rol_administrador
def gestionar_tipos(request, pk=None):
    # Lógica de carga para edición (Equivalente al IF de tu PHP)
    instancia = get_object_or_404(TipoActividad, pk=pk) if pk else None
    titulo_form = "Editar tipo de actividad" if pk else "Nuevo tipo de actividad"

    if request.method == "POST":
        form = TipoActividadForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            # El sistema de mensajes reemplaza los parámetros ?status=success en la URL
            messages.success(request, "¡Operación Exitosa!")
            return redirect("EstructuraApp:gestionar_tipos")
    else:
        form = TipoActividadForm(instance=instancia)

    # Consulta optimizada equivalente al doble LEFT JOIN que tenías en tu tabla PHP
    tipos = (
        TipoActividad.objects.select_related("id_linea__id_objetivo")
        .all()
        .order_by("-id")
    )

    context = {"form": form, "tipos": tipos, "titulo_form": titulo_form, "id_edit": pk}
    return render(request, "EstructuraApp/lista_tipos.html", context)


# Vista complementaria para eliminar de forma segura
@login_required
@requerir_rol_administrador
def eliminar_tipo(request, pk):
    tipo = get_object_or_404(TipoActividad, pk=pk)
    try:
        tipo.delete()
        messages.success(request, "Registro eliminado correctamente.")
    except ProtectedError:
        # Si hay actividades amarradas salta aquí (Equivalente a tu status=error_relacion)
        messages.error(request, "error_relacion")
    return redirect("EstructuraApp:gestionar_tipos")

@login_required
@requerir_rol_administrador
def eliminar_estructura(request, edit_tipo, pk):
    if edit_tipo == "obj":
        instancia = get_object_or_404(Objetivo, pk=pk)
    elif edit_tipo == "lin":
        instancia = get_object_or_404(Linea, pk=pk)
    else:
        messages.error(request, "Tipo de eliminación inválido.")
        return redirect("EstructuraApp:gestion_estructura")

    try:
        instancia.delete()
        messages.success(request, "Registro eliminado correctamente.")
    except ProtectedError:
        messages.error(
            request,
            "No se puede eliminar este registro porque tiene relaciones protegidas.",
        )

    return redirect("EstructuraApp:gestion_estructura")


# Endpoint AJAX que sustituye a get_jerarquia.php
@login_required
def api_get_jerarquia(request):
    objetivo_id = request.GET.get("objetivo_id")
    linea_id = request.GET.get("linea_id")

    if objetivo_id:
        lineas = Linea.objects.filter(id_objetivo_id=objetivo_id).values(
            "id", "nombre_linea"
        )
        return JsonResponse(list(lineas), safe=False)

    if linea_id:
        tipos = TipoActividad.objects.filter(id_linea_id=linea_id).values(
            "id", "nombre", "modalidad"
        )
        return JsonResponse(list(tipos), safe=False)

    return JsonResponse([], safe=False)

@login_required
def landing(request):
    
    # Si el usuario tiene el rol específico, lo mandamos directo a su herramienta
    if request.user.es_lector_asistencia:
        return redirect('Eventos:lista_eventos')
    
    ahora = timezone.now()

    context = {
        "total_programadas": ActividadProgramada.objects.filter(
            fecha_hora_inicio__gt=ahora
        ).count(),
        "total_en_curso": ActividadProgramada.objects.filter(
            fecha_hora_inicio__lte=ahora, fecha_hora_fin__gte=ahora
        ).count(),
        # Nueva métrica leyendo directamente desde la otra aplicación
        "total_responsables": Persona.objects.filter(
            roles__nombre_role__in=["Administrador", "Organizador"]
        )
        .distinct()
        .count(),
        "total_objetivos": Objetivo.objects.count(),
        "total_lineas": Linea.objects.count(),
        "total_personas_registradas": Persona.objects.count()
    }
    return render(request, "EstructuraApp/landing.html", context)

def index(request):
    return render(request, 'index.html')
