

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
