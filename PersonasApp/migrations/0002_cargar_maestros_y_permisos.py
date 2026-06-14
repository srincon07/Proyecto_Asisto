from django.db import migrations

def crear_datos_maestros_y_permisos(apps, schema_editor):
    # Obtención de modelos de EstrategiaApp
    Organizacion = apps.get_model('EstructuraApp', 'Organizacion')
    Unidad = apps.get_model('EstructuraApp', 'Unidad')
    Cargo = apps.get_model('EstructuraApp', 'Cargo')
    
    # Obtención de modelos de PersonasApp y Auth
    Rol = apps.get_model('PersonasApp', 'Rol')
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    # STEP 1: Crear la Organización Comodín/Maestra para albergar lo externo
    organizacion_raiz, _ = Organizacion.objects.get_or_create(
        nombre_organizacion='Organización Principal',
        defaults={
            'nit': '000000000-0',
            'direccion': 'Dirección General',
            'telefono': '0000000',
            'correo_electronico': 'admin@organizacion.com'
        }
    )

    # STEP 2: Crear la Unidad "Externa" amarrada a la organización
    unidad_externa, _ = Unidad.objects.get_or_create(
        nombre_unidad='Externa',
        id_organizacion=organizacion_raiz
    )

    # STEP 3: Crear el Cargo Maestro "Externo" apuntando a la Unidad creada
    Cargo.objects.get_or_create(
        nombre_cargo='Externo',
        id_unidad=unidad_externa, # Llave foránea resuelta con éxito
    )

    # STEP 4: Crear Roles Maestros de Negocio
    Rol.objects.get_or_create(nombre_role='Administrador')
    Rol.objects.get_or_create(nombre_role='Organizador')

    # STEP 5: Crear Grupos técnicos de Django y mapear permisos nativos
    grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
    grupo_organizador, _ = Group.objects.get_or_create(name='Organizador')

    todos_los_permisos = Permission.objects.all()

    # Administrador: Todo EstrategiaApp (excepto Organizacion) y todo Eventos
    permisos_admin = [
        perm for perm in todos_los_permisos 
        if perm.content_type.app_label in ['EstructuraApp', 'Eventos'] 
        and perm.content_type.model != 'organizacion'
    ]
    grupo_admin.permissions.set(permisos_admin)

    # Organizador: Únicamente la App de Eventos
    permisos_organizador = [
        perm for perm in todos_los_permisos 
        if perm.content_type.app_label == 'Eventos'
    ]
    grupo_organizador.permissions.set(permisos_organizador)


def revertir_maestros(apps, schema_editor):
    Organizacion = apps.get_model('EstructuraApp', 'Organizacion')
    Rol = apps.get_model('PersonasApp', 'Rol')
    Group = apps.get_model('auth', 'Group')

    # Al borrar la organización en cascada (si tus on_delete lo permiten) o de forma manual:
    Organizacion.objects.filter(nombre_organizacion='Organización Principal').delete()
    Rol.objects.filter(nombre_role__in=['Administrador', 'Organizador']).delete()
    Group.objects.filter(name__in=['Administrador', 'Organizador']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('PersonasApp', '0001_initial'), 
        ('EstructuraApp', '0001_initial'), 
        ('Eventos', '0001_initial'),       
    ]

    operations = [
        migrations.RunPython(crear_datos_maestros_y_permisos, revertir_maestros),
    ]