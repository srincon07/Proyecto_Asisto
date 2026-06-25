from django import forms
from django.contrib.auth.models import Group
from .models import Persona, Discapacidad, PersonaCargo
from EstructuraApp.models import Cargo


class PersonaForm(forms.ModelForm):
    discapacidad = forms.ModelChoiceField(
        queryset=Discapacidad.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Persona
        fields = [
            "identificacion",
            "nombres",
            "apellidos",
            "organizacion_origen",
            "email",
            "telefono",
            "genero",
            "discapacidad",
        ]
        widgets = {
            "identificacion": forms.TextInput(
                attrs={
                    "class": "form-control border-primary",
                    "id": "txtIdentificacion",
                    "autofocus": True,
                }
            ),
            "nombres": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombres"}
            ),
            "apellidos": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Apellidos"}
            ),
            "organizacion_origen": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "organización o Dependencia",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "ejemplo@dominio.com"}
            ),
            "telefono": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+57 300 000 0000"}
            ),
            "genero": forms.Select(attrs={"class": "form-select"}),
            "discapacidad": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Traemos todos los grupos de la BD para generar los campos dinámicos
        self.groups_db = Group.objects.all().order_by("name")

        for group in self.groups_db:
            # Checkbox para el grupo
            self.fields[f"group_{group.id}"] = forms.BooleanField(
                required=False,
                label=group.name,
                widget=forms.CheckboxInput(
                    attrs={"class": "form-check-input", "id": f"group_{group.id}"}
                ),
            )

        # Traemos todos los cargos de la BD para generar los campos dinámicos
        self.cargos_db = Cargo.objects.all().order_by("nombre_cargo")
        for cargo in self.cargos_db:
            # Checkbox para el cargo
            self.fields[f"cargo_{cargo.id}"] = forms.BooleanField(
                required=False,
                label = cargo.nombre_cargo,
                widget=forms.CheckboxInput(
                    attrs={"class": "form-check-input", "id": f"cargo_{cargo.id}"}
                ),
            )
            self.fields[f"estado_{cargo.id}"] = forms.ChoiceField(
                choices=PersonaCargo.OPCIONES_ESTADO,
                widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
                required=False,
            )

        # Si estamos editando, precargamos los valores existentes
        if self.instance and self.instance.pk:
            for group in self.instance.groups.all():
                self.initial[f"group_{group.id}"] = True
                
            cargos_asignados = PersonaCargo.objects.filter(persona=self.instance)
            for p_cargo in cargos_asignados:
                self.initial[f"cargo_{p_cargo.cargo.id}"] = True
                self.initial[f"estado_{p_cargo.cargo.id}"] = p_cargo.estado

    def save(self, commit=True):
        persona = super().save(commit=commit)

        # GESTIÓN DE GRUPOS (Reemplaza a PersonaRol)
        grupos_seleccionados = []
        for group in self.groups_db:
            if self.cleaned_data.get(f"group_{group.id}"):
                grupos_seleccionados.append(group)
        
        # Django hace el trabajo sucio automáticamente con .set()
        persona.groups.set(grupos_seleccionados)

        # Limpiar y reinsertar relaciones m2m intermedias para cargos
        PersonaCargo.objects.filter(persona=persona).delete()

        for cargo in self.cargos_db:
            if self.cleaned_data.get(f"cargo_{cargo.id}"):
                estado = self.cleaned_data.get(f"estado_{cargo.id}") or "Inactivo"
                PersonaCargo.objects.create(persona=persona, cargo=cargo, estado=estado)

        return persona
