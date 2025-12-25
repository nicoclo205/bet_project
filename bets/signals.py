from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import UsuarioSala, Ranking, SalaPartido, SalaLiga, SalaNotificacion, ApuestaFutbol


@receiver(post_save, sender=UsuarioSala)
def crear_notificacion_nuevo_miembro(sender, instance, created, **kwargs):
    """Crear notificación cuando un nuevo miembro se une a la sala"""
    if created and instance.rol == 'participante':  # Solo para nuevos participantes, no para el creador
        SalaNotificacion.objects.create(
            id_sala=instance.id_sala,
            tipo='nuevo_miembro',
            mensaje=f"{instance.id_usuario.nombre_usuario} se ha unido a la sala",
            icono='👋',
            color='text-green-500',
            usuario_relacionado=instance.id_usuario
        )


@receiver(post_save, sender=SalaPartido)
def crear_notificacion_nuevo_partido(sender, instance, created, **kwargs):
    """Crear notificación cuando se agrega un nuevo partido individual a la sala"""
    if created:
        partido = instance.id_partido
        mensaje = f"Nuevo partido agregado: {partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"

        SalaNotificacion.objects.create(
            id_sala=instance.id_sala,
            tipo='nuevo_partido',
            mensaje=mensaje,
            icono='⚽',
            color='text-blue-500',
            usuario_relacionado=instance.agregado_por,
            partido_relacionado=partido
        )


@receiver(post_save, sender=SalaLiga)
def crear_notificacion_nueva_liga(sender, instance, created, **kwargs):
    """Crear notificación cuando se agrega una nueva liga a la sala"""
    if created:
        SalaNotificacion.objects.create(
            id_sala=instance.id_sala,
            tipo='nueva_liga',
            mensaje=f"Nueva liga agregada: {instance.id_liga.nombre}",
            icono='🏆',
            color='text-purple-500'
        )


@receiver(post_save, sender=ApuestaFutbol)
def verificar_cambio_lider(sender, instance, created, **kwargs):
    """Verificar si hay un cambio de líder cuando se actualiza una apuesta"""
    if not created and instance.estado == 'ganada':  # Solo cuando se procesa una apuesta ganada
        from django.db.models import Sum, Q

        # Obtener el ranking actual de la sala
        sala = instance.id_sala

        # Calcular puntos de todos los usuarios
        usuarios_sala = UsuarioSala.objects.filter(id_sala=sala).values_list('id_usuario', flat=True)

        ranking_actual = []
        for usuario_id in usuarios_sala:
            puntos = ApuestaFutbol.objects.filter(
                id_usuario_id=usuario_id,
                id_sala=sala,
                estado='ganada'
            ).aggregate(total=Sum('puntos_ganados'))['total'] or 0

            ranking_actual.append({
                'usuario_id': usuario_id,
                'puntos': puntos
            })

        # Ordenar por puntos descendente
        ranking_actual.sort(key=lambda x: x['puntos'], reverse=True)

        if len(ranking_actual) > 0:
            nuevo_lider_id = ranking_actual[0]['usuario_id']

            # Obtener la última notificación de nuevo líder
            ultima_notif_lider = SalaNotificacion.objects.filter(
                id_sala=sala,
                tipo='nuevo_lider'
            ).order_by('-fecha').first()

            # Si no hay notificación previa o el líder es diferente
            if not ultima_notif_lider or (ultima_notif_lider.usuario_relacionado and
                                          ultima_notif_lider.usuario_relacionado.id_usuario != nuevo_lider_id):
                from .models import Usuario
                nuevo_lider = Usuario.objects.get(id_usuario=nuevo_lider_id)

                SalaNotificacion.objects.create(
                    id_sala=sala,
                    tipo='nuevo_lider',
                    mensaje=f"¡{nuevo_lider.nombre_usuario} es el nuevo líder con {ranking_actual[0]['puntos']} puntos!",
                    icono='👑',
                    color='text-yellow-500',
                    usuario_relacionado=nuevo_lider
                )


@receiver(pre_save, sender=ApuestaFutbol)
def detectar_resultado_partido(sender, instance, **kwargs):
    """Crear notificación cuando un partido finaliza con resultado"""
    if instance.pk:  # Solo si ya existe (es una actualización)
        try:
            apuesta_anterior = ApuestaFutbol.objects.get(pk=instance.pk)

            # Si el estado cambió de 'pendiente' a 'ganada' o 'perdida'
            if apuesta_anterior.estado == 'pendiente' and instance.estado in ['ganada', 'perdida']:
                partido = instance.id_partido

                # Verificar si ya existe notificación para este partido y sala
                existe_notif = SalaNotificacion.objects.filter(
                    id_sala=instance.id_sala,
                    tipo='resultado_partido',
                    partido_relacionado=partido
                ).exists()

                if not existe_notif:
                    mensaje = f"Resultado: {partido.equipo_local.nombre} {partido.goles_local} - {partido.goles_visitante} {partido.equipo_visitante.nombre}"

                    SalaNotificacion.objects.create(
                        id_sala=instance.id_sala,
                        tipo='resultado_partido',
                        mensaje=mensaje,
                        icono='⚽',
                        color='text-orange-500',
                        partido_relacionado=partido
                    )
        except ApuestaFutbol.DoesNotExist:
            pass
