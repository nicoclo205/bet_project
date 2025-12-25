"""
Tareas asíncronas de Celery para scraping y procesamiento automático usando SofaScore
"""
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='update_sofascore_full')
def update_sofascore_full():
    """
    Actualización completa de partidos desde SofaScore
    Actualiza últimos 2 días y próximos 7 días
    Ejecutar cada 6 horas
    """
    logger.info('🔄 Actualización completa de SofaScore (2 días atrás + 7 días adelante)')
    try:
        call_command('update_sofascore_football', '--days-back=2', '--days-forward=7')
        logger.info('✅ Actualización completa exitosa')
        return {'status': 'success', 'timestamp': timezone.now().isoformat()}
    except Exception as e:
        logger.error(f'❌ Error en actualización completa: {str(e)}')
        return {'status': 'error', 'error': str(e)}


@shared_task(name='update_sofascore_quick')
def update_sofascore_quick():
    """
    Actualización rápida de partidos de ayer, hoy y mañana
    Ejecutar cada 3 horas en horario de partidos
    """
    logger.info('⚡ Actualización rápida de SofaScore (ayer + hoy + mañana)')
    try:
        call_command('update_sofascore_football', '--days-back=1', '--days-forward=1')
        logger.info('✅ Actualización rápida completada')
        return {'status': 'success', 'timestamp': timezone.now().isoformat()}
    except Exception as e:
        logger.error(f'❌ Error en actualización rápida: {str(e)}')
        return {'status': 'error', 'error': str(e)}


@shared_task(name='update_live_matches')
def update_live_matches():
    """
    Actualiza partidos en curso cada 5 minutos
    Solo ejecuta si hay partidos en curso o programados para hoy
    """
    from bets.models import ApiPartido, PartidoStatus

    logger.info('⚽ Actualizando partidos en curso y de hoy')
    try:
        # Verificar si hay partidos en curso o programados para hoy
        partidos_activos = ApiPartido.objects.filter(
            estado__in=[PartidoStatus.EN_CURSO, PartidoStatus.PROGRAMADO],
            fecha__date=timezone.now().date()
        ).count()

        if partidos_activos == 0:
            logger.info('ℹ️  No hay partidos activos hoy')
            return {'status': 'no_matches', 'timestamp': timezone.now().isoformat()}

        logger.info(f'🔴 {partidos_activos} partidos activos, actualizando...')

        # Actualizar solo partidos de hoy usando --only-pending para optimizar
        call_command('update_sofascore_football', '--days-back=0', '--days-forward=0', '--only-pending')

        logger.info('✅ Partidos activos actualizados')
        return {
            'status': 'success',
            'matches_updated': partidos_activos,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f'❌ Error actualizando partidos activos: {str(e)}')
        return {'status': 'error', 'error': str(e)}


@shared_task(name='process_finished_matches')
def process_finished_matches():
    """
    Procesa partidos finalizados y actualiza apuestas
    Ejecutar cada hora
    """
    from bets.models import ApiPartido, ApuestaFutbol, PartidoStatus

    logger.info('🎯 Procesando partidos finalizados')
    try:
        # Obtener partidos finalizados en las últimas 24 horas
        hace_24h = timezone.now() - timedelta(hours=24)
        partidos_finalizados = ApiPartido.objects.filter(
            estado=PartidoStatus.FINALIZADO,
            fecha__gte=hace_24h
        )

        apuestas_procesadas = 0

        for partido in partidos_finalizados:
            # Obtener apuestas pendientes de este partido
            apuestas = ApuestaFutbol.objects.filter(
                id_partido=partido,
                estado='pendiente'
            )

            for apuesta in apuestas:
                # Calcular puntos
                puntos = apuesta.calcular_y_actualizar_puntos()
                if puntos > 0:
                    apuestas_procesadas += 1

        logger.info(f'✅ {apuestas_procesadas} apuestas procesadas')
        return {
            'status': 'success',
            'matches': partidos_finalizados.count(),
            'bets_processed': apuestas_procesadas,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f'❌ Error procesando partidos: {str(e)}')
        return {'status': 'error', 'error': str(e)}


@shared_task(name='cleanup_old_notifications')
def cleanup_old_notifications():
    """
    Limpia notificaciones antiguas (más de 30 días)
    Ejecutar una vez al día
    """
    from bets.models import SalaNotificacion

    logger.info('🧹 Limpiando notificaciones antiguas')
    try:
        hace_30_dias = timezone.now() - timedelta(days=30)
        notificaciones_eliminadas = SalaNotificacion.objects.filter(
            fecha__lt=hace_30_dias
        ).delete()

        count = notificaciones_eliminadas[0] if notificaciones_eliminadas else 0
        logger.info(f'✅ {count} notificaciones antiguas eliminadas')
        return {
            'status': 'success',
            'deleted': count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f'❌ Error limpiando notificaciones: {str(e)}')
        return {'status': 'error', 'error': str(e)}


@shared_task(name='update_specific_league')
def update_specific_league(league_id, days_back=1, days_forward=7):
    """
    Actualización de una liga específica desde SofaScore
    Útil para actualización manual
    """
    logger.info(f'🏆 Actualizando liga {league_id}')
    try:
        call_command(
            'update_sofascore_football',
            f'--league-id={league_id}',
            f'--days-back={days_back}',
            f'--days-forward={days_forward}'
        )
        logger.info(f'✅ Liga {league_id} actualizada')
        return {'status': 'success', 'league_id': league_id}
    except Exception as e:
        logger.error(f'❌ Error actualizando liga {league_id}: {str(e)}')
        return {'status': 'error', 'error': str(e)}
