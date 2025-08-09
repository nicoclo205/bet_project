from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Pais, Escenario, Usuario, Sala, UsuarioSala, Deporte, Competencia, 
    Equipo, Deportista, Partidos, PartidoFutbol, PartidoTenis, PartidoBaloncesto, 
    CarreraF1, ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1, 
    Ranking, MensajeChat
)
from .validators import validate_username, validate_password, validate_email, validate_name, validate_lastname, validate_phoneNum

class PaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pais
        fields = '__all__'

class EscenarioSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    
    class Meta:
        model = Escenario
        fields = '__all__'

class DeporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deporte
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'username', 'nombre_usuario', 'email', 'correo', 
                 'fecha_registro', 'puntos_totales', 'nombre', 'apellido', 'celular', 'foto_perfil']
        read_only_fields = ['fecha_registro']

class UsuarioCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, validators=[validate_username])
    password = serializers.CharField(write_only=True, style={'input_type': 'password'}, validators=[validate_password])
    email = serializers.EmailField(write_only=True, validators=[validate_email])
    nombre = serializers.CharField(write_only=True, validators=[validate_name])
    apellido = serializers.CharField(write_only=True, validators=[validate_lastname])
    celular = serializers.CharField(write_only=True, validators=[validate_phoneNum])
    
    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'correo', 'contrasena', 'nombre', 'apellido', 'celular', 
                 'username', 'password', 'email', 'foto_perfil']
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

class SalaSerializer(serializers.ModelSerializer):
    creador_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    
    class Meta:
        model = Sala
        fields = '__all__'

class UsuarioSalaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = UsuarioSala
        fields = '__all__'

class CompetenciaSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    deporte_nombre = serializers.ReadOnlyField(source='id_deporte.nombre')
    
    class Meta:
        model = Competencia
        fields = '__all__'

class EquipoSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    deporte_nombre = serializers.ReadOnlyField(source='id_deporte.nombre')
    
    class Meta:
        model = Equipo
        fields = '__all__'

class DeportistaSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    equipo_nombre = serializers.ReadOnlyField(source='id_equipo.nombre')
    deporte_nombre = serializers.ReadOnlyField(source='id_deporte.nombre')
    
    class Meta:
        model = Deportista
        fields = '__all__'

class PartidosSerializer(serializers.ModelSerializer):
    equipo_local_nombre = serializers.ReadOnlyField(source='equipo_local.nombre')
    equipo_visitante_nombre = serializers.ReadOnlyField(source='equipo_visitante.nombre')
    deportista_local_nombre = serializers.ReadOnlyField(source='deportista_local.nombre')
    deportista_visitante_nombre = serializers.ReadOnlyField(source='deportista_visitante.nombre')
    competencia_nombre = serializers.ReadOnlyField(source='id_competencia.nombre')
    escenario_nombre = serializers.ReadOnlyField(source='id_escenario.nombre')
    
    # Nested objects for better frontend consumption
    equipo_local = EquipoSerializer(read_only=True)
    equipo_visitante = EquipoSerializer(read_only=True)
    deportista_local = DeportistaSerializer(read_only=True)
    deportista_visitante = DeportistaSerializer(read_only=True)
    id_competencia = CompetenciaSerializer(read_only=True)
    id_escenario = EscenarioSerializer(read_only=True)
    
    class Meta:
        model = Partidos
        fields = '__all__'

class PartidoFutbolSerializer(serializers.ModelSerializer):
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    
    class Meta:
        model = PartidoFutbol
        fields = '__all__'

class PartidoTenisSerializer(serializers.ModelSerializer):
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    
    class Meta:
        model = PartidoTenis
        fields = '__all__'

class PartidoBaloncestoSerializer(serializers.ModelSerializer):
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    
    class Meta:
        model = PartidoBaloncesto
        fields = '__all__'

class CarreraF1Serializer(serializers.ModelSerializer):
    escenario_nombre = serializers.ReadOnlyField(source='id_escenario.nombre')
    competencia_nombre = serializers.ReadOnlyField(source='id_competencia.nombre')
    
    class Meta:
        model = CarreraF1
        fields = '__all__'

class ApuestaFutbolSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = ApuestaFutbol
        fields = '__all__'

class ApuestaTenisSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = ApuestaTenis
        fields = '__all__'

class ApuestaBaloncestoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = ApuestaBaloncesto
        fields = '__all__'

class ApuestaF1Serializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    carrera_info = serializers.ReadOnlyField(source='id_carrera.id_escenario.nombre')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = ApuestaF1
        fields = '__all__'

class RankingSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = Ranking
        fields = '__all__'

class MensajeChatSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='id_usuario.nombre_usuario')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    
    class Meta:
        model = MensajeChat
        fields = '__all__'