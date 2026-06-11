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


@shared_task(name='send_daily_match_reminders')
def send_daily_match_reminders():
    """
    Sends a daily email to each verified user listing tomorrow's matches:
    - Matches they have already placed a prediction for (in their salas)
    - Matches other sala members have bet on but they haven't yet
    Runs once a day at 08:00 America/Santiago via Celery Beat.
    """
    from bets.models import Usuario, UsuarioSala, ApuestaFutbol, ApiPartido, PartidoStatus
    from bets.email_service import send_match_reminder_email
    from datetime import date

    logger.info('📧 Starting daily match reminder task')

    tomorrow = (timezone.now() + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime('%A, %B %d %Y')  # e.g. "Tuesday, June 11 2026"

    # Only users with verified email
    users = Usuario.objects.filter(email_verified=True).prefetch_related('usuariosala_set')

    sent = 0
    skipped = 0

    for user in users:
        try:
            memberships = UsuarioSala.objects.filter(
                id_usuario=user
            ).select_related('id_sala')

            if not memberships.exists():
                continue

            salas_data = []

            for membership in memberships:
                sala = membership.id_sala

                # All tomorrow's PROGRAMADO matches any sala member has bet on
                all_sala_partido_ids = list(
                    ApuestaFutbol.objects.filter(
                        id_sala=sala,
                        id_partido__fecha__date=tomorrow,
                        id_partido__estado=PartidoStatus.PROGRAMADO,
                    ).values_list('id_partido_id', flat=True).distinct()
                )

                if not all_sala_partido_ids:
                    continue

                # Matches this user has bet on in this sala
                user_bet_ids = set(
                    ApuestaFutbol.objects.filter(
                        id_usuario=user,
                        id_sala=sala,
                        id_partido_id__in=all_sala_partido_ids,
                    ).values_list('id_partido_id', flat=True)
                )

                missing_ids = set(all_sala_partido_ids) - user_bet_ids

                def partido_to_dict(partido, prediccion_str=''):
                    return {
                        'local': partido.equipo_local.nombre,
                        'visitante': partido.equipo_visitante.nombre,
                        'liga': partido.id_liga.nombre if partido.id_liga else '—',
                        'hora': partido.fecha.strftime('%H:%M'),
                        'prediccion': prediccion_str,
                    }

                # Build placed list with score predictions
                bets_placed = []
                user_bets_qs = ApuestaFutbol.objects.filter(
                    id_usuario=user,
                    id_sala=sala,
                    id_partido_id__in=list(user_bet_ids),
                ).select_related(
                    'id_partido__equipo_local',
                    'id_partido__equipo_visitante',
                    'id_partido__id_liga',
                )
                for bet in user_bets_qs:
                    pred = f'{bet.prediccion_local}-{bet.prediccion_visitante}'
                    bets_placed.append(partido_to_dict(bet.id_partido, pred))

                # Build missing list
                bets_missing = []
                if missing_ids:
                    missing_qs = ApiPartido.objects.filter(
                        id_partido__in=list(missing_ids)
                    ).select_related('equipo_local', 'equipo_visitante', 'id_liga')
                    for partido in missing_qs:
                        bets_missing.append(partido_to_dict(partido))

                # Sort both by kick-off time
                bets_placed.sort(key=lambda x: x['hora'])
                bets_missing.sort(key=lambda x: x['hora'])

                salas_data.append({
                    'sala_nombre': sala.nombre,
                    'bets_placed': bets_placed,
                    'bets_missing': bets_missing,
                })

            if not salas_data or all(
                not s['bets_placed'] and not s['bets_missing'] for s in salas_data
            ):
                skipped += 1
                continue

            send_match_reminder_email(
                user_email=user.correo,
                username=user.nombre_usuario,
                salas_data=salas_data,
                tomorrow_str=tomorrow_str,
            )
            sent += 1

        except Exception as e:
            logger.error(f'Error sending reminder to {user.correo}: {e}')

    logger.info(f'Daily match reminders done: {sent} sent, {skipped} skipped (no matches)')
    return {'status': 'success', 'sent': sent, 'skipped': skipped}
