from django.contrib import admin
from .models import Usuario, Sala, Partidos, Equipos, Apuestas, Ranking, MensajesChat, Pais, Competiciones, UsuarioSala

admin.site.register(Usuario)
admin.site.register(Sala)
admin.site.register(UsuarioSala)
admin.site.register(Partidos)
admin.site.register(Equipos)
admin.site.register(Apuestas)
admin.site.register(Ranking)
admin.site.register(MensajesChat)
admin.site.register(Pais)
admin.site.register(Competiciones)