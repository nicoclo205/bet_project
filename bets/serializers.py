from rest_framework import serializers
from .models import Pais, Usuario, Sala, UsuarioSala, Competiciones, Equipos, Partidos, Apuestas, Ranking, MensajesChat

class PaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pais
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre_usuario', 'correo', 'fecha_registro', 'puntos_totales']
        read_only_fields = ['fecha_registro']

class UsuarioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre_usuario', 'correo', 'contrasena', 'fecha_registro', 'puntos_totales']
        read_only_fields = ['fecha_registro']
        extra_kwargs = {'contrasena': {'write_only': True}}

class SalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = '__all__'

class UsuarioSalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioSala
        fields = '__all__'

class CompeticionesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competiciones
        fields = '__all__'

class EquiposSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipos
        fields = '__all__'

class PartidosSerializer(serializers.ModelSerializer):
    equipo_local_nombre = serializers.ReadOnlyField(source='equipo_local.nombre')
    equipo_visitante_nombre = serializers.ReadOnlyField(source='equipo_visitante.nombre')
    competicion_nombre = serializers.ReadOnlyField(source='id_competiciones.nombre')
    
    class Meta:
        model = Partidos
        fields = '__all__'

class ApuestasSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = Apuestas
        fields = '__all__'

class RankingSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = Ranking
        fields = '__all__'

class MensajesChatSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    
    class Meta:
        model = MensajesChat
        fields = '__all__'