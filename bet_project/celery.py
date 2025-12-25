"""
Configuración de Celery para tareas asíncronas y programadas
"""
import os
from celery import Celery
from celery.schedules import crontab

# Configurar Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')

# Crear instancia de Celery
app = Celery('bet_project')

# Cargar configuración desde Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# Configuración de Celery Beat (tareas programadas)
app.conf.beat_schedule = {
    # ============================================================
    # SCRAPING DE PARTIDOS DESDE SOFASCORE
    # ============================================================

    # Actualización completa cada 6 horas (2 días atrás + 7 días adelante)
    'update-sofascore-full-00h': {
        'task': 'update_sofascore_full',
        'schedule': crontab(hour='0', minute='0'),  # 00:00
    },
    'update-sofascore-full-06h': {
        'task': 'update_sofascore_full',
        'schedule': crontab(hour='6', minute='0'),  # 06:00
    },
    'update-sofascore-full-12h': {
        'task': 'update_sofascore_full',
        'schedule': crontab(hour='12', minute='0'),  # 12:00
    },
    'update-sofascore-full-18h': {
        'task': 'update_sofascore_full',
        'schedule': crontab(hour='18', minute='0'),  # 18:00
    },

    # Actualización rápida cada 3 horas (ayer + hoy + mañana)
    'update-sofascore-quick-15h': {
        'task': 'update_sofascore_quick',
        'schedule': crontab(hour='15', minute='0'),  # 15:00
    },
    'update-sofascore-quick-21h': {
        'task': 'update_sofascore_quick',
        'schedule': crontab(hour='21', minute='0'),  # 21:00
    },

    # ============================================================
    # PARTIDOS EN VIVO
    # ============================================================

    # Actualizar partidos en curso cada 5 minutos (de 12:00 a 00:00)
    'update-live-matches': {
        'task': 'update_live_matches',
        'schedule': crontab(minute='*/5', hour='12-23'),  # Cada 5 min de 12:00 a 23:59
    },

    # ============================================================
    # PROCESAMIENTO DE RESULTADOS
    # ============================================================

    # Procesar partidos finalizados cada hora
    'process-finished-matches': {
        'task': 'process_finished_matches',
        'schedule': crontab(minute='30'),  # Cada hora en el minuto 30
    },

    # ============================================================
    # MANTENIMIENTO
    # ============================================================

    # Limpiar notificaciones antiguas una vez al día
    'cleanup-old-notifications': {
        'task': 'cleanup_old_notifications',
        'schedule': crontab(hour='3', minute='0'),  # 03:00 AM
    },
}
