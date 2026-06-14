from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Persona, Rol, PersonaRol, PersonaCargo, Discapacidad

# Configuraciones en línea para tus tablas intermedias
class PersonaRolInline(admin.TabularInline):
    model = PersonaRol
    extra = 1

class PersonaCargoInline(admin.TabularInline):
    model = PersonaCargo
    extra = 1


@admin.register(Persona)
class PersonaPersonalizadoAdmin(UserAdmin):
    """ 
    Heredar de UserAdmin le devuelve al Superusuario los formularios 
    nativos para cambiar contraseñas de forma masiva y segura.
    """
    # 1. Configuración del comportamiento en los listados
    list_display = ('email', 'identificacion', 'nombres', 'apellidos', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'roles')
    search_fields = ('email', 'identificacion', 'nombres', 'apellidos')
    ordering = ('email',)

    # 2. Control estricto de los campos que se ven al EDITAR una persona
    fieldsets = (
        ('Credenciales de Acceso', {
            'fields': ('email', 'password') # Django renderiza el link de cambio seguro aquí
        }),
        ('Información Personal', {
            'fields': ('identificacion', 'nombres', 'apellidos', 'genero', 'telefono')
        }),
        ('Información Institucional', {
            'fields': ('organizacion_origen', 'discapacidad')
        }),
        ('Permisos de Infraestructura (TI)', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')
        }),
    )

    # 3. Control de los campos requeridos al CREAR una persona directamente en el Admin
    add_fieldsets = (
        ('Crear Nuevo Usuario', {
            'classes': ('collapse',),
            'fields': ('email', 'identificacion', 'nombres', 'apellidos', 'password'),
        }),
    )

    # 4. Inyección de tus relaciones ManyToMany con tablas intermedias
    inlines = [PersonaRolInline, PersonaCargoInline]

# @admin.register(Persona)
# class PersonaAdmin(admin.ModelAdmin):
#     list_display = ("identificacion", "nombres", "apellidos", "genero")
#     search_fields = ("identificacion", "nombres", "apellidos")
#     list_filter = ("genero",)

# @admin.register(PersonaRol)
# class PersonaRolAdmin(admin.ModelAdmin):
#     list_display = ("persona", "rol")
#     search_fields = (
#         "persona__identificacion",
#         "persona__nombres",
#         "persona__apellidos",
#         "rol__nombre_role",
#     )
#     list_filter = ("rol__nombre_role",)


# @admin.register(PersonaCargo)
# class PersonaCargoAdmin(admin.ModelAdmin):
#     list_display = ("persona", "cargo", "estado")
#     search_fields = (
#         "persona__identificacion",
#         "persona__nombres",
#         "persona__apellidos",
#         "cargo__nombre_cargo",
#     )
#     list_filter = ("estado",)


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre_role",)
    search_fields = ("nombre_role",)
    list_filter = ("nombre_role",)

@admin.register(Discapacidad)
class DiscapacidadAdmin(admin.ModelAdmin):
    list_display = ("nombre_discapacidad", "estado")
    search_fields = ("nombre_discapacidad",)
    list_filter = ("estado",)
