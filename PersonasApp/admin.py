from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Persona, PersonaCargo, Discapacidad

class PersonaCargoInline(admin.TabularInline):
    model = PersonaCargo
    extra = 1

@admin.register(Persona)
class PersonaPersonalizadoAdmin(UserAdmin):
    # 1. Configuración del comportamiento en los listados
    list_display = ('email', 'identificacion', 'nombres', 'apellidos', 'is_staff', 'is_active', 'is_superuser', 'lista_grupos')
    # Añadimos 'groups' al filtro para poder buscar personas por grupo rápidamente
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'identificacion', 'nombres', 'apellidos')
    ordering = ('email',)

    # 2. Control estricto de los campos que se ven al EDITAR una persona
    fieldsets = (
        ('Credenciales de Acceso', {
            'fields': ('email', 'password')
        }),
        ('Información Personal', {
            'fields': ('identificacion', 'nombres', 'apellidos', 'genero', 'telefono')
        }),
        ('Roles y Grupos', { # Sección nueva o actualizada
            'fields': ('groups',)
        }),
        ('Información Institucional', {
            'fields': ('organizacion_origen', 'discapacidad')
        }),
        ('Permisos de Infraestructura (TI)', {
            'fields': ('is_active', 'is_staff',)
        }),
    )

    # 3. Metodo para mostrar los grupos en la lista (Opcional, para mejor visibilidad)
    def lista_grupos(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    lista_grupos.short_description = "Grupos"
    
    # 4. Control de los campos requeridos al CREAR una persona directamente en el Admin
    add_fieldsets = (
        ('Crear Nuevo Usuario', {
            'classes': ('collapse',),
            'fields': ('email', 'identificacion', 'nombres', 'apellidos', 'password'),
        }),
    )

    # 5. Inyección de tus otras relaciones
    inlines = [PersonaCargoInline]

@admin.register(Discapacidad)
class DiscapacidadAdmin(admin.ModelAdmin):
    list_display = ("nombre_discapacidad", "estado")
    search_fields = ("nombre_discapacidad",)
    list_filter = ("estado",)
