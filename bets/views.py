from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
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


# Vista de autenticación
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
    except Usuario.DoesNotExist:
        # Si no existe el perfil, puedes crearlo o manejar el error
        return Response(
            {"error": "Perfil de usuario no encontrado"}, 
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Devuelve el token y datos básicos del usuario
    return Response({
        "token": token.key,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "id_usuario": usuario.id_usuario,
        "nombre_usuario": usuario.nombre_usuario
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


# ViewSets para los modelos
class PaisViewSet(viewsets.ModelViewSet):
    queryset = Pais.objects.all()
    serializer_class = PaisSerializer


class EscenarioViewSet(viewsets.ModelViewSet):
    queryset = Escenario.objects.all()
    serializer_class = EscenarioSerializer


class DeporteViewSet(viewsets.ModelViewSet):
    queryset = Deporte.objects.all()
    serializer_class = DeporteSerializer


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


class EquipoViewSet(viewsets.ModelViewSet):
    queryset = Equipo.objects.all()
    serializer_class = EquipoSerializer


class DeportistaViewSet(viewsets.ModelViewSet):
    queryset = Deportista.objects.all()
    serializer_class = DeportistaSerializer


class PartidosViewSet(viewsets.ModelViewSet):
    queryset = Partidos.objects.all()
    serializer_class = PartidosSerializer


class PartidoFutbolViewSet(viewsets.ModelViewSet):
    queryset = PartidoFutbol.objects.all()
    serializer_class = PartidoFutbolSerializer


class PartidoTenisViewSet(viewsets.ModelViewSet):
    queryset = PartidoTenis.objects.all()
    serializer_class = PartidoTenisSerializer


class PartidoBaloncestoViewSet(viewsets.ModelViewSet):
    queryset = PartidoBaloncesto.objects.all()
    serializer_class = PartidoBaloncestoSerializer


class CarreraF1ViewSet(viewsets.ModelViewSet):
    queryset = CarreraF1.objects.all()
    serializer_class = CarreraF1Serializer


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