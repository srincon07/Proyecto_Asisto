from django import forms
from django.core.exceptions import ValidationError
from .models import TipoActividad, ActividadProgramada
from PersonasApp.models import Persona
from django.db.models import Q


class ActividadProgramadaForm(forms.ModelForm):
    class Meta:
        model = ActividadProgramada
        fields = [
            "id_tipo_actividad",
            "nombre_evento",
            "id_responsable",
            "requiere_preregistro",
            "minutos_anticipacion_cierre",
            "permite_qr_invertido",  # <- Agregado
            "confirmacion_asistencia_temporal",  # <- Agregado
            "minutos_duracion_enlace",  # <- Agregado
            "fecha_hora_inicio",
            "fecha_hora_fin",
            "lugar_desarrollo",
            "pin_confirmacion",
        ]

        widgets = {
            "nombre_evento": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Manejo de SharePoint",
                }
            ),
            "id_tipo_actividad": forms.Select(
                attrs={"class": "form-select", "id": "tip", "required": True}
            ),
            "id_responsable": forms.Select(
                attrs={"class": "form-control", "id": "select-responsable"}
            ),
            "requiere_preregistro": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "id": "id_requiere_preregistro",
                }  # ID unificado para JS
            ),
            "minutos_anticipacion_cierre": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ej: 30", "min": 0}
            ),
            "permite_qr_invertido": forms.CheckboxInput(
                attrs={"class": "form-check-input", "id": "id_permite_qr_invertido"}
            ),
            "confirmacion_asistencia_temporal": forms.CheckboxInput(
                attrs={"class": "form-check-input", "id": "id_asistencia_temporal"}
            ),
            "minutos_duracion_enlace": forms.NumberInput(
                attrs={"class": "form-control", "id": "id_minutos_duracion", "min": 1}
            ),
            "fecha_hora_inicio": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "fecha_hora_fin": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "pin_confirmacion": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Código PIN"}
            ),
            "lugar_desarrollo": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Aula 101"}
            ),
        }

    def __init__(self, *args, **kwargs):
        # ... Mantén intacta tu lógica de inicialización y filtros AJAX actual ...
        super().__init__(*args, **kwargs)
        # (Tu código previo de responsables_filtrados y selected_tipo)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Nota: Ajusta 'roles__nombre_rol' según cómo se llamen los campos relacionales en tu PersonasApp
        responsables_filtrados = (
            Persona.objects.filter(
                Q(groups__name__icontains="Administrador")
                | Q(groups__name__icontains="Organizador")
            )
            .distinct()
            .order_by("nombres")
        )

        self.fields["id_responsable"].queryset = responsables_filtrados
        self.fields["id_responsable"].empty_label = "Seleccione o escriba nombre..."

        # Dejamos el campo vacío inicialmente; se llenará dinámicamente vía JS/AJAX
        selected_tipo = self.data.get(self.add_prefix("id_tipo_actividad"))

        if selected_tipo:
            self.fields["id_tipo_actividad"].queryset = TipoActividad.objects.filter(
                pk=selected_tipo
            )
        elif self.instance and self.instance.pk:
            self.fields["id_tipo_actividad"].queryset = TipoActividad.objects.filter(
                pk=self.instance.id_tipo_actividad.pk
            )
        else:
            self.fields["id_tipo_actividad"].queryset = TipoActividad.objects.none()

    # ===== PASO CLAVE: Sobreescribir el método de validación general =====
    def clean(self):
        # Primero ejecutamos la validación base de Django
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get("fecha_hora_inicio")
        fecha_fin = cleaned_data.get("fecha_hora_fin")

        # Validamos que ambos campos hayan sido diligenciados antes de comparar
        if fecha_inicio and fecha_fin:
            if fecha_fin < fecha_inicio:
                # Opción A: Vincula el error directamente al campo específico en la interfaz
                self.add_error(
                    "fecha_hora_fin",
                    "La fecha de finalización no puede ser anterior a la fecha de inicio.",
                )

                # Opción B (Alternativa): Si prefieres un error global de formulario, descomenta la siguiente línea:
                # raise ValidationError("Error cronológico: La actividad no puede terminar antes de haber iniciado.")

        return cleaned_data


class CargaMasivaAsistentesForm(forms.Form):
    archivo_csv = forms.FileField(
        label="Seleccionar archivo de asistentes",
        help_text="Asegúrese de que el archivo sea un formato .csv separado por comas (,).",
    )
