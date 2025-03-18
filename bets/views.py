from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Pais, Usuario, Sala, UsuarioSala, Competiciones, Equipos, Partidos, Apuestas, Ranking, MensajesChat
from .serializers import (
    PaisSerializer, UsuarioSerializer, UsuarioCreateSerializer, SalaSerializer, 
    UsuarioSalaSerializer, CompeticionesSerializer, EquiposSerializer, 
    PartidosSerializer, ApuestasSerializer, RankingSerializer, MensajesChatSerializer
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

class PaisViewSet(viewsets.ModelViewSet):
    queryset = Pais.objects.all()
    serializer_class = PaisSerializer

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

class CompeticionesViewSet(viewsets.ModelViewSet):
    queryset = Competiciones.objects.all()
    serializer_class = CompeticionesSerializer

class EquiposViewSet(viewsets.ModelViewSet):
    queryset = Equipos.objects.all()
    serializer_class = EquiposSerializer

class PartidosViewSet(viewsets.ModelViewSet):
    queryset = Partidos.objects.all()
    serializer_class = PartidosSerializer

class ApuestasViewSet(viewsets.ModelViewSet):
    queryset = Apuestas.objects.all()
    serializer_class = ApuestasSerializer
    permission_classes = [IsAuthenticated]

class RankingViewSet(viewsets.ModelViewSet):
    queryset = Ranking.objects.all()
    serializer_class = RankingSerializer
    permission_classes = [IsAuthenticated]

class MensajesChatViewSet(viewsets.ModelViewSet):
    queryset = MensajesChat.objects.all()
    serializer_class = MensajesChatSerializer
    permission_classes = [IsAuthenticated]