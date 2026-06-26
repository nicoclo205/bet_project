from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user_email, verification_token, username):
    """
    Send email verification link to user
    """
    subject = 'Verify your FriendlyBet account'

    # For now, using a simple HTML template
    # You can customize this URL based on your frontend routing
    verification_url = f"{getattr(settings, 'FRONTEND_URL', settings.CORS_ALLOWED_ORIGINS[0])}/verify-email?token={verification_token}"

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; text-align: center;">Welcome to FriendlyBet!</h2>
                <p style="color: #555; font-size: 16px;">Hi {username},</p>
                <p style="color: #555; font-size: 16px;">
                    Thank you for registering! Please verify your email address by clicking the button below:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #777; font-size: 14px;">
                    Or copy and paste this link in your browser:<br>
                    <a href="{verification_url}" style="color: #3498db;">{verification_url}</a>
                </p>
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    This link will expire in 24 hours.
                </p>
                <p style="color: #777; font-size: 14px;">
                    If you didn't create an account, please ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    FriendlyBet - Sports Betting & Predictions
                </p>
            </div>
        </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    try:
        logger.info(f"Sending verification email to {user_email}")
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent successfully to {user_email}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send verification email to {user_email}: {str(e)}")
        raise


def send_password_reset_email(user_email, reset_token, username):
    """
    Send password reset link to user
    """
    subject = 'Reset your FriendlyBet password'

    # Password reset URL
    reset_url = f"{getattr(settings, 'FRONTEND_URL', settings.CORS_ALLOWED_ORIGINS[0])}/reset-password?token={reset_token}"

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; text-align: center;">Password Reset Request</h2>
                <p style="color: #555; font-size: 16px;">Hi {username},</p>
                <p style="color: #555; font-size: 16px;">
                    We received a request to reset your password. Click the button below to create a new password:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #777; font-size: 14px;">
                    Or copy and paste this link in your browser:<br>
                    <a href="{reset_url}" style="color: #e74c3c;">{reset_url}</a>
                </p>
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    This link will expire in 1 hour.
                </p>
                <p style="color: #e74c3c; font-size: 14px; font-weight: bold;">
                    If you didn't request a password reset, please ignore this email and your password will remain unchanged.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    FriendlyBet - Sports Betting & Predictions
                </p>
            </div>
        </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    try:
        logger.info(f"Sending password reset email to {user_email}")
        logger.info(f"Reset URL: {reset_url}")
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password reset email sent successfully to {user_email}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
        raise


def send_room_invitation_email(invited_email, invite_token, room_name, inviter_name):
    """
    Send a room invitation email with a link to register and auto-join.
    """
    subject = f"You've been invited to join {room_name} on FriendlyBet!"

    frontend_url = getattr(settings, 'FRONTEND_URL', settings.CORS_ALLOWED_ORIGINS[0])
    invite_url = f"{frontend_url}/login?invite={invite_token}"

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; text-align: center;">🏆 FriendlyBet Invitation</h2>
                <p style="color: #555; font-size: 16px;">Hi there!</p>
                <p style="color: #555; font-size: 16px;">
                    <strong>{inviter_name}</strong> has invited you to join the betting room
                    <strong>"{room_name}"</strong> on FriendlyBet.
                </p>
                <p style="color: #555; font-size: 16px;">
                    Click the button below to create your account and you'll be automatically added to the room:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invite_url}"
                       style="background-color: #27ae60; color: white; padding: 14px 36px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block;">
                        Accept Invitation &amp; Sign Up
                    </a>
                </div>
                <p style="color: #777; font-size: 14px;">
                    Or copy and paste this link in your browser:<br>
                    <a href="{invite_url}" style="color: #27ae60;">{invite_url}</a>
                </p>
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    This invitation link will expire in 7 days.
                </p>
                <p style="color: #777; font-size: 14px;">
                    If you weren't expecting this invitation, you can safely ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    FriendlyBet - Sports Betting &amp; Predictions
                </p>
            </div>
        </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    try:
        logger.info(f"Sending room invitation email to {invited_email} for room '{room_name}'")
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invited_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Room invitation email sent to {invited_email}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send room invitation email to {invited_email}: {str(e)}")
        raise


def send_match_reminder_email(user_email, username, salas_data, tomorrow_str):
    """
    Envia recordatorio diario de partidos de manana.
    salas_data: list of dicts with keys:
        sala_nombre, bets_placed (list of match dicts), bets_missing (list of match dicts)
    Each match dict: {local, visitante, liga, hora, prediccion}
    """
    from django.utils.html import strip_tags

    total_placed = sum(len(s['bets_placed']) for s in salas_data)
    total_missing = sum(len(s['bets_missing']) for s in salas_data)

    if total_placed == 0 and total_missing == 0:
        return

    subject = f'[FriendlyBet] Partidos manana {tomorrow_str} / Tomorrow matches'

    BALL = '&#x26BD;'
    CHECK = '&#x2705;'
    CLOCK = '&#x23F3;'
    HOUSE = '&#x1F3E0;'
    TROPHY = '&#x1F3C6;'
    CAL = '&#x1F4C5;'

    def match_row_green(m):
        return (
            f'<div style="padding:6px 10px;margin:3px 0;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:4px;font-size:13px;color:#374151;">'
            f'{BALL} <strong>{m["local"]}</strong> vs <strong>{m["visitante"]}</strong>'
            f'<span style="color:#6b7280;font-size:12px;"> &middot; {m["liga"]} &middot; {m["hora"]} UTC</span>'
            f'<span style="color:#16a34a;font-size:12px;margin-left:6px;">{{label}}: {m["prediccion"]}</span>'
            f'</div>'
        )

    def match_row_amber(m):
        return (
            f'<div style="padding:6px 10px;margin:3px 0;background:#fffbeb;border-left:3px solid #d97706;border-radius:4px;font-size:13px;color:#374151;">'
            f'{BALL} <strong>{m["local"]}</strong> vs <strong>{m["visitante"]}</strong>'
            f'<span style="color:#6b7280;font-size:12px;"> &middot; {m["liga"]} &middot; {m["hora"]} UTC</span>'
            f'<span style="color:#d97706;font-size:12px;margin-left:6px;">{{label}}</span>'
            f'</div>'
        )

    def sala_block(sala, lang):
        rows = ''
        placed_label = 'Tu marcador' if lang == 'es' else 'Your score'
        missing_label = '&iexcl;Otros ya apostaron!' if lang == 'es' else 'Others have bet!'
        placed_heading = f'{CHECK} Ya tienes prediccion:' if lang == 'es' else f'{CHECK} Already predicted:'
        missing_heading = f'{CLOCK} Faltan por registrar:' if lang == 'es' else f'{CLOCK} Missing predictions:'

        if sala['bets_placed']:
            rows += f'<p style="margin:8px 0 4px;font-size:13px;color:#16a34a;font-weight:600;">{placed_heading}</p>'
            for m in sala['bets_placed']:
                rows += match_row_green(m).format(label=placed_label)
        if sala['bets_missing']:
            rows += f'<p style="margin:12px 0 4px;font-size:13px;color:#d97706;font-weight:600;">{missing_heading}</p>'
            for m in sala['bets_missing']:
                rows += match_row_amber(m).format(label=missing_label)
        return rows

    def sala_card(sala, lang):
        inner = sala_block(sala, lang)
        if not inner:
            return ''
        return (
            f'<div style="margin-bottom:20px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">'
            f'<div style="background:#16a34a;color:white;padding:8px 14px;font-size:14px;font-weight:700;">'
            f'{HOUSE} {sala["sala_nombre"]}'
            f'</div>'
            f'<div style="padding:12px 14px;">{inner}</div>'
            f'</div>'
        )

    salas_es = ''.join(sala_card(s, 'es') for s in salas_data)
    salas_en = ''.join(sala_card(s, 'en') for s in salas_data)

    cta_url = getattr(settings, 'FRONTEND_URL', 'https://friendlybet.260569.xyz')

    pending_es = (
        f'<span style="color:#d97706;font-weight:600;">Tienes {total_missing} prediccion(es) pendiente(s).</span>'
        if total_missing > 0 else
        '<span style="color:#16a34a;font-weight:600;">Todo al dia! &#x1F389;</span>'
    )
    pending_en = (
        f'<span style="color:#d97706;font-weight:600;">You have {total_missing} missing prediction(s).</span>'
        if total_missing > 0 else
        '<span style="color:#16a34a;font-weight:600;">All caught up! &#x1F389;</span>'
    )

    html_message = f"""
    <html>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
      <div style="max-width:600px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <div style="background:linear-gradient(135deg,#16a34a,#15803d);padding:28px 30px;text-align:center;">
          <h1 style="margin:0;color:white;font-size:22px;font-weight:800;">{TROPHY} FriendlyBet</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">{tomorrow_str}</p>
        </div>
        <div style="padding:28px 30px;">
          <div style="border-bottom:2px solid #e5e7eb;padding-bottom:24px;margin-bottom:24px;">
            <h2 style="margin:0 0 6px;font-size:17px;color:#111827;">{CAL} Tus partidos de manana</h2>
            <p style="margin:0 0 16px;font-size:13px;color:#6b7280;">
              Hola <strong>{username}</strong>, aqui estan los partidos de manana en tus salas. {pending_es}
            </p>
            {salas_es}
            <div style="text-align:center;margin-top:20px;">
              <a href="{cta_url}" style="background:#16a34a;color:white;padding:11px 28px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;display:inline-block;">
                Registrar predicciones &rarr;
              </a>
            </div>
          </div>
          <div>
            <h2 style="margin:0 0 6px;font-size:17px;color:#111827;">{CAL} Your matches tomorrow</h2>
            <p style="margin:0 0 16px;font-size:13px;color:#6b7280;">
              Hi <strong>{username}</strong>, here are tomorrow's matches in your rooms. {pending_en}
            </p>
            {salas_en}
            <div style="text-align:center;margin-top:20px;">
              <a href="{cta_url}" style="background:#16a34a;color:white;padding:11px 28px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;display:inline-block;">
                Place your predictions &rarr;
              </a>
            </div>
          </div>
        </div>
        <div style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:14px 30px;text-align:center;">
          <p style="margin:0;font-size:11px;color:#9ca3af;">
            FriendlyBet &middot; Sports Predictions with Friends
          </p>
        </div>
      </div>
    </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    try:
        logger.info(f"Sending match reminder to {user_email} ({total_placed} placed, {total_missing} missing)")
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Match reminder sent to {user_email}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send match reminder to {user_email}: {str(e)}")
        raise


def send_phase_transition_email(sala_id, ronda_patron='group'):
    """
    Sends a group-stage wrap-up email to every member of the given room.

    Computes final group-stage standings for the room, then dispatches a
    bilingual (ES + EN) email to each verified member with the top-3 and
    the point gaps relative to the leader.

    Args:
        sala_id: Primary key of the Sala to notify.
        ronda_patron: String fragment used to identify group-stage matches
                      via a case-insensitive ronda__icontains filter.
                      Defaults to 'group' (matches "Group Stage - 1", etc.).

    Returns:
        dict: {'sent': int, 'failed': int}
    """
    from django.utils.html import strip_tags as _strip
    from bets.models import Sala, UsuarioSala, ApuestaFutbol, ApiPartido, ApuestaStatus

    sala = Sala.objects.select_related('id_usuario').get(id_sala=sala_id)
    members = list(
        UsuarioSala.objects.filter(id_sala=sala).select_related('id_usuario')
    )

    if not members:
        logger.warning(f"send_phase_transition_email: sala {sala_id} has no members")
        return {'sent': 0, 'failed': 0}

    # Identify all group-stage match IDs scoped to this sala's bets
    group_match_ids = list(
        ApiPartido.objects.filter(ronda__icontains=ronda_patron)
        .values_list('id_partido', flat=True)
    )

    # Compute standings: total points per user from group-stage bets in this sala
    standings = []
    for m in members:
        pts = (
            ApuestaFutbol.objects.filter(
                id_sala=sala,
                id_usuario=m.id_usuario,
                id_partido_id__in=group_match_ids,
                estado=ApuestaStatus.GANADA,
            ).aggregate(total=Sum('puntos_ganados'))['total']
            or 0
        )
        standings.append({'usuario': m.id_usuario, 'puntos': pts})

    standings.sort(key=lambda x: x['puntos'], reverse=True)

    # Extract top-3 data
    def _entry(idx):
        return standings[idx] if idx < len(standings) else None

    first = _entry(0)
    second = _entry(1)
    third = _entry(2)

    first_name = first['usuario'].nombre_usuario if first else '—'
    first_pts = first['puntos'] if first else 0
    second_name = second['usuario'].nombre_usuario if second else '—'
    second_gap = (first_pts - second['puntos']) if second else 0
    third_name = third['usuario'].nombre_usuario if third else '—'
    third_gap = (first_pts - third['puntos']) if third else 0

    # Render standings table rows (top-N)
    def _standings_rows(lang):
        medals = ['🥇', '🥈', '🥉']
        pts_label = 'pts'
        rows = ''
        for i, entry in enumerate(standings):
            medal = medals[i] if i < 3 else f'{i + 1}.'
            rows += (
                f'<tr style="border-bottom:1px solid #e5e7eb;">'
                f'<td style="padding:8px 12px;font-size:14px;color:#374151;">{medal}</td>'
                f'<td style="padding:8px 12px;font-size:14px;color:#111827;font-weight:{"700" if i == 0 else "400"};">'
                f'{entry["usuario"].nombre_usuario}</td>'
                f'<td style="padding:8px 12px;font-size:14px;color:#16a34a;font-weight:700;text-align:right;">'
                f'{entry["puntos"]} {pts_label}</td>'
                f'</tr>'
            )
        return rows

    TROPHY = '&#x1F3C6;'
    BALL = '&#x26BD;'
    cta_url = getattr(settings, 'FRONTEND_URL', 'https://friendlybet.260569.xyz')

    html_message = f"""
    <html>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
      <div style="max-width:600px;margin:30px auto;background:#fff;border-radius:12px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1d4ed8,#1e40af);padding:32px 30px;text-align:center;">
          <h1 style="margin:0;color:white;font-size:24px;font-weight:800;">{TROPHY} FriendlyBet</h1>
          <p style="margin:8px 0 0;color:rgba(255,255,255,0.9);font-size:16px;font-weight:600;">
            {sala.nombre}
          </p>
        </div>

        <div style="padding:32px 30px;">

          <!-- ===== ESPAÑOL ===== -->
          <div style="border-bottom:2px solid #e5e7eb;padding-bottom:28px;margin-bottom:28px;">
            <h2 style="margin:0 0 4px;font-size:20px;color:#111827;">{BALL} Fase de Grupos — Resultados Finales</h2>
            <p style="margin:0 0 20px;font-size:13px;color:#6b7280;">
              La fase de grupos ha concluido. Aqui esta la clasificacion final de <strong>{sala.nombre}</strong>:
            </p>

            <!-- Podium callout -->
            <div style="background:#fefce8;border:1px solid #fde68a;border-radius:8px;padding:16px 20px;margin-bottom:20px;">
              <p style="margin:0 0 6px;font-size:15px;font-weight:700;color:#92400e;">
                🥇 Lider de grupo: <span style="color:#1d4ed8;">{first_name}</span>
              </p>
              {"" if not second else f'<p style="margin:0 0 6px;font-size:13px;color:#374151;">🥈 {second_name} &mdash; a {second_gap} punto{"s" if second_gap != 1 else ""} del lider</p>'}
              {"" if not third else f'<p style="margin:0;font-size:13px;color:#374151;">🥉 {third_name} &mdash; a {third_gap} punto{"s" if third_gap != 1 else ""} del lider</p>'}
            </div>

            <!-- Full standings table -->
            <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
              <thead>
                <tr style="background:#f9fafb;">
                  <th style="padding:10px 12px;font-size:12px;color:#6b7280;text-align:left;font-weight:600;">POS</th>
                  <th style="padding:10px 12px;font-size:12px;color:#6b7280;text-align:left;font-weight:600;">JUGADOR</th>
                  <th style="padding:10px 12px;font-size:12px;color:#6b7280;text-align:right;font-weight:600;">PUNTOS</th>
                </tr>
              </thead>
              <tbody>
                {_standings_rows('es')}
              </tbody>
            </table>

            <p style="margin:20px 0 0;font-size:13px;color:#6b7280;">
              La fase eliminatoria comienza pronto. ¡Sigue apostando!
            </p>
            <div style="text-align:center;margin-top:16px;">
              <a href="{cta_url}" style="background:#1d4ed8;color:white;padding:11px 28px;border-radius:8px;
                 text-decoration:none;font-size:14px;font-weight:700;display:inline-block;">
                Ver sala &rarr;
              </a>
            </div>
          </div>

          <!-- ===== ENGLISH ===== -->
          <div>
            <h2 style="margin:0 0 4px;font-size:20px;color:#111827;">{BALL} Group Stage — Final Standings</h2>
            <p style="margin:0 0 20px;font-size:13px;color:#6b7280;">
              The group stage is over. Here are the final standings for <strong>{sala.nombre}</strong>:
            </p>

            <!-- Podium callout -->
            <div style="background:#fefce8;border:1px solid #fde68a;border-radius:8px;padding:16px 20px;margin-bottom:20px;">
              <p style="margin:0 0 6px;font-size:15px;font-weight:700;color:#92400e;">
                🥇 Group leader: <span style="color:#1d4ed8;">{first_name}</span>
              </p>
              {"" if not second else f'<p style="margin:0 0 6px;font-size:13px;color:#374151;">🥈 {second_name} &mdash; {second_gap} point{"s" if second_gap != 1 else ""} behind the leader</p>'}
              {"" if not third else f'<p style="margin:0;font-size:13px;color:#374151;">🥉 {third_name} &mdash; {third_gap} point{"s" if third_gap != 1 else ""} behind the leader</p>'}
            </div>

            <!-- Full standings table -->
            <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
              <thead>
                <tr style="background:#f9fafb;">
                  <th style="padding:10px 12px;font-size:12px;color:#6b7280;text-align:left;font-weight:600;">POS</th>
                  <th style="padding:10px 12px;font-size:12px;color:#6b7280;text-align:left;font-weight:600;">PLAYER</th>
                  <th style="padding:10px 12px;font-size:12px;color:#6b7280;text-align:right;font-weight:600;">POINTS</th>
                </tr>
              </thead>
              <tbody>
                {_standings_rows('en')}
              </tbody>
            </table>

            <p style="margin:20px 0 0;font-size:13px;color:#6b7280;">
              The knockout round is coming up. Keep predicting!
            </p>
            <div style="text-align:center;margin-top:16px;">
              <a href="{cta_url}" style="background:#1d4ed8;color:white;padding:11px 28px;border-radius:8px;
                 text-decoration:none;font-size:14px;font-weight:700;display:inline-block;">
                View room &rarr;
              </a>
            </div>
          </div>

        </div>

        <div style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:14px 30px;text-align:center;">
          <p style="margin:0;font-size:11px;color:#9ca3af;">
            FriendlyBet &middot; Sports Predictions with Friends
          </p>
        </div>
      </div>
    </body>
    </html>
    """

    subject = f'[FriendlyBet] {sala.nombre} — Fase de Grupos / Group Stage Results'
    plain_message = _strip(html_message)

    sent = 0
    failed = 0
    for m in members:
        user = m.id_usuario
        if not user.email_verified:
            continue
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.correo],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Phase transition email sent to {user.correo} (sala={sala.nombre})")
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send phase transition email to {user.correo}: {e}")
            failed += 1

    return {'sent': sent, 'failed': failed}
