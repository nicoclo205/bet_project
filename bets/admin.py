from django.contrib import admin
from .models import (
    Usuario, Sala, ApiPartido, ApiEquipo, ApiPais, ApiLiga,
    UsuarioSala, Ranking, MensajeChat, 
    ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    ApiJugador, Deporte, ApiVenue, CarreraF1, PartidoTenis, PartidoBaloncesto,
    ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion, ApiSyncLog
)

# User and Room models
admin.site.register(Usuario)
admin.site.register(Sala)
admin.site.register(UsuarioSala)

# API data models
admin.site.register(ApiPartido)
admin.site.register(ApiEquipo)
admin.site.register(ApiPais)
admin.site.register(ApiLiga)
admin.site.register(ApiJugador)
admin.site.register(ApiVenue)
admin.site.register(ApiPartidoEstadisticas)
admin.site.register(ApiPartidoEvento)
admin.site.register(ApiPartidoAlineacion)
admin.site.register(ApiSyncLog)

# Basic models
admin.site.register(Deporte)
admin.site.register(Ranking)
admin.site.register(MensajeChat)

# Sport-specific models
admin.site.register(PartidoTenis)
admin.site.register(PartidoBaloncesto)
admin.site.register(CarreraF1)

# Bet models
admin.site.register(ApuestaFutbol)
admin.site.register(ApuestaTenis)
admin.site.register(ApuestaBaloncesto)
admin.site.register(ApuestaF1)