# Eventos/services.py
from zoneinfo import ZoneInfo
from django.db.models import Count
from django.core.cache import cache
from .models import RegistroAsistencia, ActividadProgramada
from django.utils import timezone

def obtener_datos_dashboard(actividad_id=None):
    # Clave dinámica por actividad para evitar conflictos en caché
    cache_key = f'dashboard_stats_{actividad_id or "global"}'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Filtro base según se seleccione un evento o todos
        qs_asistencia = RegistroAsistencia.objects.all()
        qs_actividad = ActividadProgramada.objects.all()
        
        if actividad_id:
            qs_asistencia = qs_asistencia.filter(actividad_id=actividad_id)
            qs_actividad = qs_actividad.filter(id=actividad_id)
        
        # 1. Distribución de estados
        stats_estado = list(qs_asistencia.values('estado').annotate(cantidad=Count('id')))

        # 2. Participación por tipo de actividad
        stats_tipo = list(qs_actividad.values('id_tipo_actividad__nombre')
                          .annotate(total_asistentes=Count('asistencias')))

        # 3. Tendencia (Últimos 30 días)
        treinta_dias_atras = timezone.now() - timezone.timedelta(days=30)
        stats_tendencia = list(qs_asistencia.filter(
            estado='CONFIRMADO', 
            fecha_confirmacion__gte=treinta_dias_atras
        ).extra({'fecha': "date(fecha_confirmacion)"})
         .values('fecha')
         .annotate(total=Count('id'))
         .order_by('fecha'))
        
        local_tz = ZoneInfo("America/Bogota") # O tu zona horaria correspondiente
        time_now = timezone.now().astimezone(local_tz)

        stats = {
            "estado": stats_estado,
            "tipo": stats_tipo,
            "tendencia": stats_tendencia,
            "updated_at": time_now.strftime("%H:%M:%S")
        }
        
        cache.set(cache_key, stats, 300)
    
    return stats