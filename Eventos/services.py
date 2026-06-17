# Eventos/services.py
from django.db.models import Count, Q
from django.core.cache import cache
from .models import RegistroAsistencia, ActividadProgramada
from django.utils import timezone

def obtener_datos_dashboard():
    """
    Recopila y procesa indicadores clave. 
    Se utiliza caché para evitar consultas pesadas recurrentes.
    """
    #cache.delete('dashboard_stats')  # Eliminar esta línea para mantener la caché
    stats = cache.get('dashboard_stats')
    
    if stats is None:
        # 1. Distribución de estados de asistencia
        stats_estado = list(RegistroAsistencia.objects.values('estado')
                            .annotate(cantidad=Count('id')))

        # 2. Participación por tipo de actividad
        stats_tipo = list(ActividadProgramada.objects.values('id_tipo_actividad__nombre')
                          .annotate(total_asistentes=Count('asistencias')))

        # 3. Tendencia: Confirmaciones confirmadas en los últimos 30 días
        treinta_dias_atras = timezone.now() - timezone.timedelta(days=30)
        stats_tendencia = list(RegistroAsistencia.objects.filter(
            estado='CONFIRMADO', 
            fecha_confirmacion__gte=treinta_dias_atras
        ).extra({'fecha': "date(fecha_confirmacion)"})
         .values('fecha')
         .annotate(total=Count('id'))
         .order_by('fecha'))

        stats = {
            "estado": stats_estado,
            "tipo": stats_tipo,
            "tendencia": stats_tendencia
        }
        
        # Guardar en caché por 1 hora (3600 segundos)
        cache.set('dashboard_stats', stats, 3600)
    
    return stats