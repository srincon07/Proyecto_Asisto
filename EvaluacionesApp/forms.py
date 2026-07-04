from django import forms
from .models import Evaluacion, Pregunta, OpcionRespuesta


class EvaluacionForm(forms.ModelForm):
    class Meta:
        model = Evaluacion
        fields = ['titulo', 'activa']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

PreguntaFormSet = forms.inlineformset_factory(
    Evaluacion, 
    Pregunta, 
    fields=('texto', 'escala_maxima',), 
    extra=0, 
    can_delete=True,
    widgets={
        'texto': forms.TextInput(attrs={'class': 'form-control'}),
        'escala_maxima': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)

# Formset para las opciones de una pregunta específica
OpcionFormSet = forms.inlineformset_factory(
    Pregunta, 
    OpcionRespuesta, 
    fields=('valor', 'label'), 
    extra=0, 
    can_delete=True
)