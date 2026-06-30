from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import (
    Usuario, Sala, UsuarioSala,
    Deporte, ApiPais, ApiLiga, ApiEquipo, ApiJugador, ApiVenue,
    ApiPartido, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    PartidoTenis, PartidoBaloncesto, CarreraF1,
    ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat,
    EmailVerificationToken, PasswordResetToken, LoginEvent,
    PartidoStatus,
)

# User and Room models
admin.site.register(Usuario)
admin.site.register(Sala)
admin.site.register(UsuarioSala)

# Basic models
admin.site.register(Deporte)

# API data models
admin.site.register(ApiPais)
admin.site.register(ApiLiga)
admin.site.register(ApiEquipo)
admin.site.register(ApiJugador)
admin.site.register(ApiVenue)


class ApiPartidoAdminForm(forms.ModelForm):
    class Meta:
        model = ApiPartido
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        is_knockout = cleaned.get('is_knockout')
        estado = cleaned.get('estado')
        goles_local = cleaned.get('goles_local')
        goles_visitante = cleaned.get('goles_visitante')

        if not is_knockout or estado != PartidoStatus.FINALIZADO:
            return cleaned

        # Partido knockout finalizado: los campos ET y penales deben estar definidos
        tiene_et = cleaned.get('resultado_tiene_tiempo_extra')
        tiene_pen = cleaned.get('resultado_tiene_penales')
        ganador_pen = cleaned.get('ganador_penales')

        if goles_local is None or goles_visitante is None:
            return cleaned

        if goles_local == goles_visitante:
            # Empate en tiempo normal: obligatorio tiempo extra y penales
            if tiene_et is None:
                raise ValidationError(
                    'Partido knockout empatado: debes indicar si hubo tiempo extra '
                    '(campo "resultado_tiene_tiempo_extra").'
                )
            if tiene_pen is not True:
                raise ValidationError(
                    'Partido knockout empatado: siempre hay penales. '
                    'Marca "resultado_tiene_penales" como Sí.'
                )
            if not ganador_pen:
                raise ValidationError(
                    'Partido knockout empatado: debes seleccionar el equipo ganador '
                    'en penales (campo "ganador_penales").'
                )
            equipo_local = cleaned.get('equipo_local')
            equipo_visitante = cleaned.get('equipo_visitante')
            if ganador_pen not in (equipo_local, equipo_visitante):
                raise ValidationError(
                    'El ganador en penales debe ser uno de los dos equipos del partido.'
                )
        else:
            # Hay ganador en tiempo normal o extra: no puede haber ganador en penales
            if ganador_pen:
                raise ValidationError(
                    'Hay un ganador en el marcador: no corresponde registrar ganador en penales.'
                )
            if tiene_pen is True and not ganador_pen:
                raise ValidationError(
                    'Si hubo penales, debes seleccionar el ganador en penales.'
                )

        return cleaned


# Match models
@admin.register(ApiPartido)
class ApiPartidoAdmin(admin.ModelAdmin):
    form = ApiPartidoAdminForm
    list_display = (
        '__str__', 'estado', 'fecha', 'is_knockout',
        'resultado_tiene_tiempo_extra', 'resultado_tiene_penales', 'ganador_penales',
    )
    list_filter = ('estado', 'is_knockout', 'id_liga')
    search_fields = ('equipo_local__nombre', 'equipo_visitante__nombre')
    fieldsets = (
        ('General', {
            'fields': (
                'id_liga', 'temporada', 'ronda', 'fecha',
                'equipo_local', 'equipo_visitante',
                'goles_local', 'goles_visitante',
                'estado', 'id_venue',
            )
        }),
        ('Knockout', {
            'fields': (
                'is_knockout',
                'resultado_tiene_tiempo_extra',
                'resultado_tiene_penales',
                'ganador_penales',
            ),
            'description': (
                'Para partidos knockout finalizados: si el marcador es empate, '
                'debes indicar tiempo extra, marcar penales = Sí y elegir el ganador. '
                'Si hay ganador en el marcador, deja ganador_penales vacío.'
            ),
        }),
        ('Tracking', {
            'fields': ('eventos_cargados', 'alineaciones_cargadas', 'estadisticas_cargadas'),
            'classes': ('collapse',),
        }),
    )

admin.site.register(ApiPartidoEstadisticas)
admin.site.register(ApiPartidoEvento)
admin.site.register(ApiPartidoAlineacion)

# Sport-specific match models
admin.site.register(PartidoTenis)
admin.site.register(PartidoBaloncesto)
admin.site.register(CarreraF1)

# Bet models
admin.site.register(ApuestaFutbol)
admin.site.register(ApuestaTenis)
admin.site.register(ApuestaBaloncesto)
admin.site.register(ApuestaF1)

# Social models
admin.site.register(Ranking)
admin.site.register(MensajeChat)

# Email verification and password reset
admin.site.register(EmailVerificationToken)
admin.site.register(PasswordResetToken)


# Login tracking
@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'timestamp', 'ip_address', 'user_agent')
    list_filter = ('timestamp',)
    search_fields = ('usuario__nombre_usuario', 'usuario__correo', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('usuario', 'timestamp', 'ip_address', 'user_agent')

    def has_add_permission(self, request):
        return False
