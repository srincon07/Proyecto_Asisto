from django import forms
from .models import Objetivo, Linea, TipoActividad, Unidad


class ObjetivoForm(forms.ModelForm):
    class Meta:
        model = Objetivo
        # Definimos los campos del modelo que se mostrarán en el HTML
        fields = ["id_unidad", "nombre_objetivo"]

        # Personalizamos las etiquetas (labels)
        labels = {
            "id_unidad": "Unidad:",
            "nombre_objetivo": "Nombre del objetivo",
        }

        # Agregamos las clases de Bootstrap y atributos HTML usando widgets
        widgets = {
            "id_unidad": forms.Select(attrs={"class": "form-select", "required": True}),
            "nombre_objetivo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Fortalecimiento Humano",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenamos las unidades alfabéticamente y personalizamos la opción por defecto
        self.fields["id_unidad"].queryset = Unidad.objects.all().order_by(
            "nombre_unidad"
        )
        self.fields["id_unidad"].empty_label = "Seleccione..."


class LineaForm(forms.ModelForm):
    class Meta:
        model = Linea
        # En este formulario incluimos la llave foránea para amarrar la línea a un objetivo
        fields = ["id_objetivo", "nombre_linea"]

        labels = {
            "id_objetivo": "Pertenece al objetivo:",
            "nombre_linea": "Nombre de la línea",
        }

        widgets = {
            "id_objetivo": forms.Select(
                attrs={"class": "form-select", "required": True}
            ),
            "nombre_linea": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Deporte y Recreación",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenamos alfabéticamente las opciones del menú desplegable de Objetivos
        self.fields["id_objetivo"].queryset = Objetivo.objects.all().order_by(
            "nombre_objetivo"
        )

        # Cambiamos el texto de la opción por defecto ("---------") a algo más profesional
        self.fields["id_objetivo"].empty_label = "Seleccione..."


class TipoActividadForm(forms.ModelForm):
    class Meta:
        model = TipoActividad
        fields = ["id_linea", "nombre", "modalidad"]

        labels = {
            "id_linea": "Línea de acción",
            "nombre": "Nombre del tipo",
            "modalidad": "Modalidad",
        }

        widgets = {
            "id_linea": forms.Select(attrs={"class": "form-select", "required": True}),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Torneo de Ajedrez",
                    "required": True,
                }
            ),
            "modalidad": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenamos alfabéticamente las opciones del menú desplegable de Objetivos y luego por nombre de línea
        self.fields["id_linea"].queryset = Linea.objects.select_related(
            "id_objetivo"
        ).order_by("id_objetivo__nombre_objetivo", "nombre_linea")
        self.fields["id_linea"].empty_label = "Seleccione..."

        # Opcional: Personalizar el texto del select para que muestre [Objetivo] - Línea en lugar de solo el nombre de la línea
        self.fields["id_linea"].label_from_instance = (
            lambda obj: f"[{obj.id_objetivo.nombre_objetivo}] - {obj.nombre_linea}"
        )
