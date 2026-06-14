from django import forms
from .models import Persona, Rol, PersonaRol, Discapacidad, PersonaCargo
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
        # Traemos todos los roles de la BD para generar los campos dinámicos
        self.roles_db = Rol.objects.all().order_by("nombre_role")

        for rol in self.roles_db:
            # Checkbox para el rol
            self.fields[f"rol_{rol.id}"] = forms.BooleanField(
                required=False,
                widget=forms.CheckboxInput(
                    attrs={"class": "form-check-input", "id": f"role_{rol.id}"}
                ),
            )

        # Traemos todos los cargos de la BD para generar los campos dinámicos
        self.cargos_db = Cargo.objects.all().order_by("nombre_cargo")
        for cargo in self.cargos_db:
            # Checkbox para el cargo
            self.fields[f"cargo_{cargo.id}"] = forms.BooleanField(
                required=False,
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
            roles_asignados = PersonaRol.objects.filter(persona=self.instance)
            for p_rol in roles_asignados:
                self.initial[f"rol_{p_rol.rol.id}"] = True

            cargos_asignados = PersonaCargo.objects.filter(persona=self.instance)
            for p_cargo in cargos_asignados:
                self.initial[f"cargo_{p_cargo.cargo.id}"] = True
                self.initial[f"estado_{p_cargo.cargo.id}"] = p_cargo.estado

    def save(self, commit=True):
        persona = super().save(commit=commit)

        # Limpiar y reinsertar relaciones m2m intermedias
        PersonaRol.objects.filter(persona=persona).delete()

        for rol in self.roles_db:
            if self.cleaned_data.get(f"rol_{rol.id}"):
                PersonaRol.objects.create(persona=persona, rol=rol)

        # Limpiar y reinsertar relaciones m2m intermedias para cargos
        PersonaCargo.objects.filter(persona=persona).delete()

        for cargo in self.cargos_db:
            if self.cleaned_data.get(f"cargo_{cargo.id}"):
                estado = self.cleaned_data.get(f"estado_{cargo.id}") or "Inactivo"
                PersonaCargo.objects.create(persona=persona, cargo=cargo, estado=estado)

        return persona
