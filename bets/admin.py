from django.contrib import admin
from .models import (
    Usuario, Sala, Partidos, Equipo, Pais, Competencia, 
    UsuarioSala, Ranking, MensajeChat, 
    ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Deportista, Deporte, Escenario, CarreraF1,
    PartidoFutbol, PartidoTenis, PartidoBaloncesto
)

# You can use the basic admin registration for most models
admin.site.register(Usuario)
admin.site.register(Sala)
admin.site.register(UsuarioSala)
admin.site.register(Partidos)
admin.site.register(Equipo)
admin.site.register(Pais)
admin.site.register(Competencia)
admin.site.register(Ranking)
admin.site.register(MensajeChat)
admin.site.register(Deportista)
admin.site.register(Deporte)
admin.site.register(Escenario)

# Register different bet types
admin.site.register(ApuestaFutbol)
admin.site.register(ApuestaTenis)
admin.site.register(ApuestaBaloncesto)
admin.site.register(ApuestaF1)
admin.site.register(CarreraF1)

# Register specific sport match types
admin.site.register(PartidoFutbol)
admin.site.register(PartidoTenis)
admin.site.register(PartidoBaloncesto)