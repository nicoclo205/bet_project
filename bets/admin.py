from django.contrib import admin
from .models import (
    Usuario, Sala, UsuarioSala,
    Deporte, ApiPais, ApiLiga, ApiEquipo, ApiJugador, ApiVenue,
    ApiPartido, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    PartidoTenis, PartidoBaloncesto, CarreraF1,
    ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat,
    EmailVerificationToken, PasswordResetToken
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
admin.site.register(ApiPartido)
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
