from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from .models import Persona
from .forms import PersonaForm
from .decorators import requerir_rol_administrador  # Importación de decoradores personalizados

@login_required
@requerir_rol_administrador
def lista_personas(request):
    # Consulta optimizada ordenando por las nuevas columnas independientes
    personas = (
        Persona.objects.all()
        .prefetch_related("personarol_set__rol")
        .order_by("nombres", "apellidos")
    )
    return render(request, "PersonasApp/lista_personas.html", {"personas": personas})

@login_required
@requerir_rol_administrador
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

@login_required
@requerir_rol_administrador
def eliminar_persona(request, pk):
    persona = get_object_or_404(Persona, pk=pk)
    persona.delete()
    return redirect("PersonasApp:lista_personas")

def error_403_permiso_denegado(request, exception=None):
    """ Redirecciona visualmente al usuario cuando viola las restricciones de su rol """
    return render(request, 'errors/403.html', status=403)