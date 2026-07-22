from datetime import datetime
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
            "permite_qr_invertido",
            "confirmacion_asistencia_temporal",
            "minutos_duracion_enlace",
            "fecha_hora_inicio",
            "fecha_hora_fin",
            "lugar_desarrollo",
            "pin_confirmacion",
            "aplicar_evaluacion",
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
            "aplicar_evaluacion": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "id": "id_aplicar_evaluacion",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user  # Guardamos el usuario actual para usarlo en la validación

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
        
        # Si estamos editando un evento existente, obtener la organización
        if self.instance.pk:
            tipo_actividad = self.instance.id_tipo_actividad
            organizacion = tipo_actividad.id_linea.id_objetivo.id_unidad.id_organizacion
            self._apply_plan_restrictions(organizacion)

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

    
    
    def _apply_plan_restrictions(self, organizacion):
        """Deshabilita campos basado en el plan de la organización"""
        if organizacion.plan == 'BASICO':
            self.fields['requiere_preregistro'].disabled = True
            self.fields['pin_confirmacion'].disabled = True
            self.fields['aplicar_evaluacion'].disabled = True
            self.fields['permite_qr_invertido'].disabled = True
        
        elif organizacion.plan == 'PRO':
            # PRO no permite QR invertido
            self.fields['permite_qr_invertido'].disabled = True

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
                
        # Solo validar si NO es superusuario (superusers pueden saltarse restricciones)
        if self.user and self.user.is_superuser:
            return cleaned_data
        
        tipo_actividad = cleaned_data.get('id_tipo_actividad')
        if not tipo_actividad:
            return cleaned_data
        
        # Obtener organización
        organizacion = tipo_actividad.id_linea.id_objetivo.id_unidad.id_organizacion
        
        # 1. Validar límite mensual SOLO para eventos nuevos
        if self.instance.pk is None:  # Es un evento nuevo
            fecha_inicio = cleaned_data.get('fecha_hora_inicio')
            if fecha_inicio:
                # Contar eventos del mes actual
                eventos_mes = ActividadProgramada.objects.filter(
                    id_tipo_actividad__id_linea__id_objetivo__id_unidad__id_organizacion=organizacion,
                    fecha_hora_inicio__year=fecha_inicio.year,
                    fecha_hora_inicio__month=fecha_inicio.month
                ).count()
                
                if eventos_mes >= organizacion.limite_eventos_mes:
                    raise ValidationError(
                        f"Has alcanzado el límite de {organizacion.limite_eventos_mes} "
                        f"eventos para este mes. Plan actual: {organizacion.get_plan_display()}"
                    )
        
        # 2. Validar restricción de Evaluaciones
        if cleaned_data.get('aplicar_evaluacion') and organizacion.plan == 'BASICO':
            self.add_error('aplicar_evaluacion',
                'Las evaluaciones solo están disponibles en planes PRO o superiores.')
        
        # 3. Validar restricción de Pre-registro
        if cleaned_data.get('requiere_preregistro') and organizacion.plan == 'BASICO':
            self.add_error('requiere_preregistro',
                'El pre-registro solo está disponible en planes PRO o superiores.')
        
        # 4. Validar restricción de QR Invertido
        if cleaned_data.get('permite_qr_invertido') and organizacion.plan != 'ENTERPRISE':
            self.add_error('permite_qr_invertido',
                'El Pase Digital (QR) solo está disponible en plan ENTERPRISE.')

        return cleaned_data


class CargaMasivaAsistentesForm(forms.Form):
    archivo_csv = forms.FileField(
        label="Seleccionar archivo de asistentes",
        help_text="Asegúrese de que el archivo sea un formato .csv separado por comas (,).",
    )
