# PersonasApp/templatetags/form_utils.py
from django import template

# Esta línea es obligatoria para que Django registre los filtros
register = template.Library()


@register.filter(name="addstr")  # Forzamos el nombre explícitamente
def addstr(arg1, arg2):
    return f"{arg1}{arg2}"
