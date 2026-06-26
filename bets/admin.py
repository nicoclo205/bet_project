from django.contrib import admin
from .models import (
    Usuario, Sala, UsuarioSala,
    Deporte, ApiPais, ApiLiga, ApiEquipo, ApiJugador, ApiVenue,
    ApiPartido, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    PartidoTenis, PartidoBaloncesto, CarreraF1,
    ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat,
    EmailVerificationToken, PasswordResetToken, LoginEvent
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

# Match models
@admin.register(ApiPartido)
class ApiPartidoAdmin(admin.ModelAdmin):
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
            'classes': ('collapse',),
            'description': 'Fill these in when entering the final result of a knockout match.',
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
