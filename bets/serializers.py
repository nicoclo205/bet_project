from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Pais, Usuario, Sala, UsuarioSala, Competiciones, Equipos, Partidos, Apuestas, Ranking, MensajesChat

class PaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pais
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'username', 'nombre_usuario', 'email', 'correo', 'fecha_registro', 'puntos_totales', 'nombre', 'apellido', 'celular']
        read_only_fields = ['fecha_registro']

class UsuarioCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField(write_only=True)
    
    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'correo', 'contrasena', 'nombre', 'apellido', 'celular', 'username', 'password', 'email']
        extra_kwargs = {'contrasena': {'write_only': True}}
    
    def create(self, validated_data):
        # Extraer datos para el User de Django
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        
        # Crear User de Django
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Si no se proporciona nombre_usuario, usar el username
        if 'nombre_usuario' not in validated_data or not validated_data['nombre_usuario']:
            validated_data['nombre_usuario'] = username
            
        # Si no se proporciona correo, usar el email
        if 'correo' not in validated_data or not validated_data['correo']:
            validated_data['correo'] = email
        
        # Crear Usuario vinculado
        usuario = Usuario.objects.create(
            user=user,
            **validated_data
        )
        
        return usuario

# El resto de tus serializers permanecen igual
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