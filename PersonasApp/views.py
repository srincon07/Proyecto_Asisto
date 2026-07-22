from django.shortcuts import render, redirect, get_object_or_404
from .models import Persona
from django.contrib import messages
from .forms import PersonaForm
from .decorators import es_miembro_grupo  # Importación de decoradores personalizados

@es_miembro_grupo('Administrador')
def lista_personas(request):
    # Consulta optimizada ordenando por las nuevas columnas independientes
    personas = (
        Persona.objects.filter(is_superuser=False)
        .prefetch_related("groups")
        .order_by("nombres", "apellidos")
    )
    return render(request, "PersonasApp/lista_personas.html", {"personas": personas})

@es_miembro_grupo('Administrador')
def registrar_editar_persona(request, pk=None):
    if pk:
        persona = get_object_or_404(Persona, pk=pk)
        accion = "editar"
    else:
        persona = Persona()
        accion = "crear"

    status = None
    if request.method == "POST":
        form = PersonaForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            return redirect("PersonasApp:lista_personas")
        else:
            if "identificacion" in form.errors:
                status = "error_duplicado"
    else:
        form = PersonaForm(instance=persona)

    return render(
        request,
        "PersonasApp/registro_persona.html",
        {"form": form, "persona": persona, "id_persona": pk or 0, "status": status},
    )

@es_miembro_grupo('Administrador')
def eliminar_persona(request, pk):
    persona = get_object_or_404(Persona, pk=pk)
    
    # 1. Validar si tiene Cargos asociados (Usa el related_name por defecto de Django)
    tiene_cargos = persona.personacargo_set.exists()
    
    # 2. Usa el related_name "historial_actividades" que definiste en RegistroAsistencia
    tiene_asistencias = persona.historial_actividades.exists()

    # Si cumple cualquiera de las dos, impedimos el borrado físico para proteger la integridad
    if tiene_cargos or tiene_asistencias:
        messages.error(request, "error_relacion_asistente")
        return redirect("PersonasApp:lista_personas")
    
    try:
        nombre_completo = f"{persona.nombres} {persona.apellidos}"
        persona.delete()
        messages.success(request, f"El registro de {nombre_completo} fue eliminado correctamente.")
    except Exception as e:
        # En caso de cualquier otro error de base de datos
        messages.error(request, "No se pudo eliminar el registro debido a un error de integridad en el servidor.")
        
    return redirect("PersonasApp:lista_personas")

def error_403_permiso_denegado(request, exception=None):
    """ Redirecciona visualmente al usuario cuando viola las restricciones de su rol """
    return render(request, 'errors/403.html', status=403)