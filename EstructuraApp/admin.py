from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Organizacion,
    Unidad,
    Cargo,
    Objetivo,
    Linea,
    TipoActividad,
)


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("nombre_organizacion", "nit", "plan", "limite_eventos_mes", "correo_electronico", "mostrar_logo_thumbnail")
    search_fields = ("nombre_organizacion", "nit", "correo_electronico")
    
    # Organizar el formulario de edición por secciones
    fieldsets = (
        ('Información General', {
            'fields': ('nombre_organizacion', 'nit', 'direccion', 'telefono', 'correo_electronico', 'sitio_web') # Añade aquí tus otros campos de texto
        }),
        ('Identidad Visual', {
            'fields': ('logo', 'preview_logo_form'),
        }),
        ('Plan y Límites', {
            'fields': ('plan', 'limite_eventos_mes')
        }),
        ('Tratamiento de Datos', {
            'fields': ('correo_tratamiento_datos', 'url_politica_datos', 'texto_consentimiento'),
            'description': 'Configuración para el tratamiento de datos personales y consentimiento'
        }),
    )
    
    # Campo de solo lectura para ver el logo dentro del formulario de edición
    readonly_fields = ('preview_logo_form',)    
    
    # Función para previsualizar el logo en la lista de registros
    def mostrar_logo_thumbnail(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width: 50px; height: auto; max-height: 50px; border-radius: 4px;" />', obj.logo.url)
        return "Sin Logo"
    mostrar_logo_thumbnail.short_description = 'Miniatura del Logo'

    # Función para previsualizar el logo dentro del formulario
    def preview_logo_form(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width: 200px; height: auto; border: 1px solid #ccc; padding: 5px; border-radius: 8px;" />', obj.logo.url)
        return "No se ha cargado ningún logo aún."
    preview_logo_form.short_description = 'Vista Previa Actual'


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre_unidad", "id_organizacion")
    search_fields = ("nombre_unidad", "id_organizacion__nombre_organizacion")
    list_filter = ("id_organizacion",)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "id_unidad")
    search_fields = ("nombre_cargo", "id_unidad__nombre_unidad")
    list_filter = ("id_unidad",)


@admin.register(Objetivo)
class ObjetivoAdmin(admin.ModelAdmin):
    list_display = ("nombre_objetivo", "id_unidad")
    search_fields = ("nombre_objetivo", "id_unidad__nombre_unidad")
    list_filter = ("id_unidad",)


@admin.register(Linea)
class LineaAdmin(admin.ModelAdmin):
    list_display = ("nombre_linea", "id_objetivo")
    search_fields = ("nombre_linea", "id_objetivo__nombre_objetivo")
    list_filter = ("id_objetivo",)


@admin.register(TipoActividad)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "id_linea")
    search_fields = ("nombre", "id_linea__nombre_linea")
    list_filter = ("id_linea",)
