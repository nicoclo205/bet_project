from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ApiPais, ApiVenue, Usuario, Sala, UsuarioSala, Deporte, ApiLiga, 
    ApiEquipo, ApiJugador, ApiPartido, PartidoTenis, PartidoBaloncesto, 
    CarreraF1, ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1, 
    Ranking, MensajeChat, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    ApiSyncLog
)
from .validators import validate_username, validate_password, validate_email, validate_name, validate_lastname, validate_phoneNum

class ApiPaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiPais
        fields = '__all__'

class ApiVenueSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    
    class Meta:
        model = ApiVenue
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

class ApiLigaSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    deporte_nombre = serializers.ReadOnlyField(source='id_deporte.nombre')
    
    class Meta:
        model = ApiLiga
        fields = '__all__'

class ApiEquipoSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    deporte_nombre = serializers.ReadOnlyField(source='id_deporte.nombre')
    
    class Meta:
        model = ApiEquipo
        fields = '__all__'

class ApiJugadorSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.ReadOnlyField(source='id_pais.nombre')
    equipo_nombre = serializers.ReadOnlyField(source='id_equipo.nombre')
    deporte_nombre = serializers.ReadOnlyField(source='id_deporte.nombre')
    
    class Meta:
        model = ApiJugador
        fields = '__all__'

class ApiPartidoSerializer(serializers.ModelSerializer):
    equipo_local_nombre = serializers.ReadOnlyField(source='equipo_local.nombre')
    equipo_visitante_nombre = serializers.ReadOnlyField(source='equipo_visitante.nombre')
    liga_nombre = serializers.ReadOnlyField(source='id_liga.nombre')
    venue_nombre = serializers.ReadOnlyField(source='id_venue.nombre') if 'id_venue' else None
    
    class Meta:
        model = ApiPartido
        fields = '__all__'

class ApiPartidoEstadisticasSerializer(serializers.ModelSerializer):
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    equipo_nombre = serializers.ReadOnlyField(source='id_equipo.nombre')
    
    class Meta:
        model = ApiPartidoEstadisticas
        fields = '__all__'

class ApiPartidoEventoSerializer(serializers.ModelSerializer):
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    equipo_nombre = serializers.ReadOnlyField(source='id_equipo.nombre')
    jugador_nombre = serializers.ReadOnlyField(source='id_jugador.nombre') if 'id_jugador' else None
    
    class Meta:
        model = ApiPartidoEvento
        fields = '__all__'

class ApiPartidoAlineacionSerializer(serializers.ModelSerializer):
    partido_info = serializers.ReadOnlyField(source='id_partido.__str__')
    equipo_nombre = serializers.ReadOnlyField(source='id_equipo.nombre')
    
    class Meta:
        model = ApiPartidoAlineacion
        fields = '__all__'

class PartidoTenisSerializer(serializers.ModelSerializer):
    jugador_local_nombre = serializers.ReadOnlyField(source='jugador_local.nombre')
    jugador_visitante_nombre = serializers.ReadOnlyField(source='jugador_visitante.nombre')
    liga_nombre = serializers.ReadOnlyField(source='id_liga.nombre') if 'id_liga' else None
    venue_nombre = serializers.ReadOnlyField(source='id_venue.nombre') if 'id_venue' else None
    
    class Meta:
        model = PartidoTenis
        fields = '__all__'

class PartidoBaloncestoSerializer(serializers.ModelSerializer):
    equipo_local_nombre = serializers.ReadOnlyField(source='equipo_local.nombre')
    equipo_visitante_nombre = serializers.ReadOnlyField(source='equipo_visitante.nombre')
    liga_nombre = serializers.ReadOnlyField(source='id_liga.nombre') if 'id_liga' else None
    venue_nombre = serializers.ReadOnlyField(source='id_venue.nombre') if 'id_venue' else None
    
    class Meta:
        model = PartidoBaloncesto
        fields = '__all__'

class CarreraF1Serializer(serializers.ModelSerializer):
    venue_nombre = serializers.ReadOnlyField(source='id_venue.nombre') if 'id_venue' else None
    liga_nombre = serializers.ReadOnlyField(source='id_liga.nombre') if 'id_liga' else None
    
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
    carrera_info = serializers.ReadOnlyField(source='id_carrera.__str__')
    sala_nombre = serializers.ReadOnlyField(source='id_sala.nombre')
    piloto_p1_nombre = serializers.ReadOnlyField(source='prediccion_p1.nombre')
    piloto_p2_nombre = serializers.ReadOnlyField(source='prediccion_p2.nombre') if 'prediccion_p2' else None
    piloto_p3_nombre = serializers.ReadOnlyField(source='prediccion_p3.nombre') if 'prediccion_p3' else None
    
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

class ApiSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiSyncLog
        fields = '__all__'