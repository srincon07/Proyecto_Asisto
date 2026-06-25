from django.db import migrations

def crear_datos_maestros_y_permisos(apps, schema_editor):
    # Obtención de modelos de EstrategiaApp
    Organizacion = apps.get_model('EstructuraApp', 'Organizacion')
    Unidad = apps.get_model('EstructuraApp', 'Unidad')
    Cargo = apps.get_model('EstructuraApp', 'Cargo')
    
    # Obtención de modelos de Auth
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

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

    # STEP 4: Crear Grupos técnicos de Django y mapear permisos nativos
    grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
    grupo_organizador, _ = Group.objects.get_or_create(name='Organizador')
    grupo_lector_asistencia, _ = Group.objects.get_or_create(name='Lector-Asistencia')

    todos_los_permisos = Permission.objects.all()

    # Administrador: Todo EstrategiaApp (excepto Organizacion) y todo Eventos
    permisos_admin = [
        perm for perm in todos_los_permisos 
        if perm.content_type.app_label in ['EstructuraApp', 'Eventos', 'PersonasApp'] 
        and perm.content_type.model != 'organizacion'
    ]
    grupo_admin.permissions.set(permisos_admin)

    # Organizador: Únicamente la App de Eventos
    permisos_organizador = [
        perm for perm in todos_los_permisos 
        if perm.content_type.app_label == 'Eventos'
    ]
    grupo_organizador.permissions.set(permisos_organizador)
    
    # Lector-Asistencia: Únicamente change Control de Asistencia en la App Eventos
    try:
        # Buscamos el ContentType de RegistroAsistencia en la app Eventos
        ct_asistencia = ContentType.objects.get(
            app_label='Eventos', 
            model='registroasistencia' # Nota: siempre en minúsculas
        )
        # Obtenemos el permiso específico de 'change' (cambiar/editar)
        permiso_change = Permission.objects.get(
            content_type=ct_asistencia, 
            codename='change_registroasistencia'
        )
        grupo_lector_asistencia.permissions.add(permiso_change)
    except (ContentType.DoesNotExist, Permission.DoesNotExist):
        # Manejo de error si el modelo no existe aún en la base de datos
        print("Advertencia: No se pudo asignar permiso al grupo Lector-Asistencia.")

def revertir_maestros(apps, schema_editor):
    Organizacion = apps.get_model('EstructuraApp', 'Organizacion')
    Group = apps.get_model('auth', 'Group')

    # Al borrar la organización en cascada (si tus on_delete lo permiten) o de forma manual:
    Organizacion.objects.filter(nombre_organizacion='Organización Principal').delete()
    Group.objects.filter(name__in=['Administrador', 'Organizador', 'Lector-Asistencia']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('PersonasApp', '0001_initial'), 
        ('EstructuraApp', '0001_initial'), 
        ('Eventos', '0001_initial'),       
    ]

    operations = [
        migrations.RunPython(crear_datos_maestros_y_permisos, revertir_maestros),
    ]