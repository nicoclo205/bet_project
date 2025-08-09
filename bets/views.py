from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import (
    Pais, Escenario, Usuario, Sala, UsuarioSala, Deporte, Competencia,
    Equipo, Deportista, Partidos, PartidoFutbol, PartidoTenis, PartidoBaloncesto,
    CarreraF1, ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat
)
from .serializers import (
    PaisSerializer, EscenarioSerializer, UsuarioSerializer, UsuarioCreateSerializer,
    SalaSerializer, UsuarioSalaSerializer, DeporteSerializer, CompetenciaSerializer,
    EquipoSerializer, DeportistaSerializer, PartidosSerializer, PartidoFutbolSerializer,
    PartidoTenisSerializer, PartidoBaloncestoSerializer, CarreraF1Serializer,
    ApuestaFutbolSerializer, ApuestaTenisSerializer, ApuestaBaloncestoSerializer,
    ApuestaF1Serializer, RankingSerializer, MensajeChatSerializer
)

# Authentication endpoints
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    API endpoint para iniciar sesión y obtener un token
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {"error": "Por favor proporciona nombre de usuario y contraseña"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Autenticación con Django's User model
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response(
            {"error": "Credenciales inválidas"}, 
            status=status.HTTP_401_UNAUTHORIZED,
        )
    
    # Genera o obtiene el token para el usuario autenticado
    token, created = Token.objects.get_or_create(user=user)
    
    # Obtiene el perfil de Usuario asociado
    try:
        usuario = Usuario.objects.get(user=user)
        nombre_usuario = usuario.nombre_usuario
        id_usuario = usuario.id_usuario
    except Usuario.DoesNotExist:
        # Si no existe el perfil, usa los datos del User de Django
        nombre_usuario = user.username
        id_usuario = user.id
    
    # Devuelve el token y datos básicos del usuario
    return Response({
        "token": token.key,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "id_usuario": id_usuario,
        "nombre_usuario": nombre_usuario
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    API endpoint para cerrar sesión y eliminar el token
    """
    try:
        # Elimina el token del usuario
        request.user.auth_token.delete()
        return Response({"success": "Sesión cerrada correctamente"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usuario_me(request):
    """
    API endpoint para obtener el usuario actual
    """
    try:
        usuario = Usuario.objects.get(user=request.user)
        nombre_usuario = usuario.nombre_usuario
        id_usuario = usuario.id_usuario
    except Usuario.DoesNotExist:
        nombre_usuario = request.user.username
        id_usuario = request.user.id
    
    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
        "id_usuario": id_usuario,
        "nombre_usuario": nombre_usuario
    })

# ViewSets for all models
class PaisViewSet(viewsets.ModelViewSet):
    queryset = Pais.objects.all()
    serializer_class = PaisSerializer
    permission_classes = [AllowAny]

class EscenarioViewSet(viewsets.ModelViewSet):
    queryset = Escenario.objects.all()
    serializer_class = EscenarioSerializer
    permission_classes = [AllowAny]

class DeporteViewSet(viewsets.ModelViewSet):
    queryset = Deporte.objects.all()
    serializer_class = DeporteSerializer
    permission_classes = [AllowAny]

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return UsuarioCreateSerializer
        return UsuarioSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [AllowAny()]
        return [IsAuthenticated()]

class SalaViewSet(viewsets.ModelViewSet):
    queryset = Sala.objects.all()
    serializer_class = SalaSerializer
    permission_classes = [IsAuthenticated]

class UsuarioSalaViewSet(viewsets.ModelViewSet):
    queryset = UsuarioSala.objects.all()
    serializer_class = UsuarioSalaSerializer
    permission_classes = [IsAuthenticated]

class CompetenciaViewSet(viewsets.ModelViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer
    permission_classes = [AllowAny]

class EquipoViewSet(viewsets.ModelViewSet):
    queryset = Equipo.objects.all()
    serializer_class = EquipoSerializer
    permission_classes = [AllowAny]

class DeportistaViewSet(viewsets.ModelViewSet):
    queryset = Deportista.objects.all()
    serializer_class = DeportistaSerializer
    permission_classes = [AllowAny]

class PartidosViewSet(viewsets.ModelViewSet):
    queryset = Partidos.objects.all()
    serializer_class = PartidosSerializer
    permission_classes = [AllowAny]

class PartidoFutbolViewSet(viewsets.ModelViewSet):
    queryset = PartidoFutbol.objects.all()
    serializer_class = PartidoFutbolSerializer
    permission_classes = [AllowAny]

class PartidoTenisViewSet(viewsets.ModelViewSet):
    queryset = PartidoTenis.objects.all()
    serializer_class = PartidoTenisSerializer
    permission_classes = [AllowAny]

class PartidoBaloncestoViewSet(viewsets.ModelViewSet):
    queryset = PartidoBaloncesto.objects.all()
    serializer_class = PartidoBaloncestoSerializer
    permission_classes = [AllowAny]

class CarreraF1ViewSet(viewsets.ModelViewSet):
    queryset = CarreraF1.objects.all()
    serializer_class = CarreraF1Serializer
    permission_classes = [AllowAny]

class ApuestaFutbolViewSet(viewsets.ModelViewSet):
    queryset = ApuestaFutbol.objects.all()
    serializer_class = ApuestaFutbolSerializer
    permission_classes = [IsAuthenticated]

class ApuestaTenisViewSet(viewsets.ModelViewSet):
    queryset = ApuestaTenis.objects.all()
    serializer_class = ApuestaTenisSerializer
    permission_classes = [IsAuthenticated]

class ApuestaBaloncestoViewSet(viewsets.ModelViewSet):
    queryset = ApuestaBaloncesto.objects.all()
    serializer_class = ApuestaBaloncestoSerializer
    permission_classes = [IsAuthenticated]

class ApuestaF1ViewSet(viewsets.ModelViewSet):
    queryset = ApuestaF1.objects.all()
    serializer_class = ApuestaF1Serializer
    permission_classes = [IsAuthenticated]

class RankingViewSet(viewsets.ModelViewSet):
    queryset = Ranking.objects.all()
    serializer_class = RankingSerializer
    permission_classes = [IsAuthenticated]

class MensajeChatViewSet(viewsets.ModelViewSet):
    queryset = MensajeChat.objects.all()
    serializer_class = MensajeChatSerializer
    permission_classes = [IsAuthenticated]