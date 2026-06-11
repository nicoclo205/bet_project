

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
