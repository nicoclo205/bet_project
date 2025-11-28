from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
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
    
    @action(detail=False, methods=['get'])
    def mis_salas(self, request):
        """
        Devuelve las salas a las que pertenece el usuario autenticado
        """
        usuario = request.user.perfil
        salas_propias = Sala.objects.filter(id_usuario=usuario)
        
        # Obtener salas a las que el usuario pertenece mediante UsuarioSala
        pertenencias = UsuarioSala.objects.filter(id_usuario=usuario)
        salas_miembro = [pertenencia.id_sala for pertenencia in pertenencias]
        
        # Combinar ambos conjuntos de salas
        todas_salas = list(salas_propias) + salas_miembro
        
        # Serializar los resultados
        serializer = self.get_serializer(todas_salas, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def unirse(self, request, pk=None):
        """
        Permite a un usuario unirse a una sala usando su código
        """
        codigo = request.data.get('codigo')
        if not codigo:
            return Response({"error": "Se requiere el código de sala"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            sala = Sala.objects.get(codigo_sala=codigo)
        except Sala.DoesNotExist:
            return Response({"error": "Sala no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        
        usuario = request.user.perfil
        
        # Verificar si ya es miembro
        if UsuarioSala.objects.filter(id_usuario=usuario, id_sala=sala).exists():
            return Response({"error": "Ya eres miembro de esta sala"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear la relación UsuarioSala
        UsuarioSala.objects.create(id_usuario=usuario, id_sala=sala)
        
        return Response({"success": f"Te has unido a la sala {sala.nombre}"}, status=status.HTTP_201_CREATED)

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
    
    def get_queryset(self):
        queryset = Partidos.objects.all()
        
        # Filter by sport if provided
        deporte = self.request.query_params.get('deporte', None)
        if deporte is not None:
            # Direct sport filtering (much more efficient)
            queryset = queryset.filter(id_deporte=deporte)
        
        # Filter by competition if provided
        competencia = self.request.query_params.get('competencia', None)
        if competencia is not None:
            queryset = queryset.filter(id_competencia=competencia)
        
        # Filter by status if provided
        estado = self.request.query_params.get('estado', None)
        if estado is not None:
            queryset = queryset.filter(estado=estado)
        
        # Order by date
        queryset = queryset.order_by('fecha_partido')
        
        return queryset

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
    
    @action(detail=False, methods=['get'])
    def mis_apuestas(self, request):
        """
        Obtiene las apuestas de fútbol del usuario autenticado
        """
        usuario = request.user.perfil
        sala_id = request.query_params.get('sala_id')
        
        query = Q(id_usuario=usuario)
        if sala_id:
            query &= Q(id_sala=sala_id)
            
        apuestas = ApuestaFutbol.objects.filter(query).order_by('-fecha_apuesta')
        serializer = self.get_serializer(apuestas, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_partido(self, request):
        """
        Obtiene las apuestas para un partido específico en una sala
        """
        partido_id = request.query_params.get('partido_id')
        sala_id = request.query_params.get('sala_id')
        
        if not partido_id or not sala_id:
            return Response({"error": "Se requieren los IDs del partido y la sala"}, status=status.HTTP_400_BAD_REQUEST)
            
        apuestas = ApuestaFutbol.objects.filter(id_partido=partido_id, id_sala=sala_id)
        serializer = self.get_serializer(apuestas, many=True)
        return Response(serializer.data)

class ApuestaTenisViewSet(viewsets.ModelViewSet):
    queryset = ApuestaTenis.objects.all()
    serializer_class = ApuestaTenisSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def mis_apuestas(self, request):
        """
        Obtiene las apuestas de tenis del usuario autenticado
        """
        usuario = request.user.perfil
        sala_id = request.query_params.get('sala_id')
        
        query = Q(id_usuario=usuario)
        if sala_id:
            query &= Q(id_sala=sala_id)
            
        apuestas = ApuestaTenis.objects.filter(query).order_by('-fecha_apuesta')
        serializer = self.get_serializer(apuestas, many=True)
        return Response(serializer.data)

class ApuestaBaloncestoViewSet(viewsets.ModelViewSet):
    queryset = ApuestaBaloncesto.objects.all()
    serializer_class = ApuestaBaloncestoSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def mis_apuestas(self, request):
        """
        Obtiene las apuestas de baloncesto del usuario autenticado
        """
        usuario = request.user.perfil
        sala_id = request.query_params.get('sala_id')
        
        query = Q(id_usuario=usuario)
        if sala_id:
            query &= Q(id_sala=sala_id)
            
        apuestas = ApuestaBaloncesto.objects.filter(query).order_by('-fecha_apuesta')
        serializer = self.get_serializer(apuestas, many=True)
        return Response(serializer.data)

class ApuestaF1ViewSet(viewsets.ModelViewSet):
    queryset = ApuestaF1.objects.all()
    serializer_class = ApuestaF1Serializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def mis_apuestas(self, request):
        """
        Obtiene las apuestas de F1 del usuario autenticado
        """
        usuario = request.user.perfil
        sala_id = request.query_params.get('sala_id')
        
        query = Q(id_usuario=usuario)
        if sala_id:
            query &= Q(id_sala=sala_id)
            
        apuestas = ApuestaF1.objects.filter(query).order_by('-fecha_apuesta')
        serializer = self.get_serializer(apuestas, many=True)
        return Response(serializer.data)

class RankingViewSet(viewsets.ModelViewSet):
    queryset = Ranking.objects.all()
    serializer_class = RankingSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def por_sala(self, request):
        """
        Obtiene el ranking de una sala específica por periodo
        """
        sala_id = request.query_params.get('sala_id')
        periodo = request.query_params.get('periodo')  # formato YYYY-MM-DD
        
        if not sala_id:
            return Response({"error": "Se requiere el ID de la sala"}, status=status.HTTP_400_BAD_REQUEST)
            
        query = Q(id_sala=sala_id)
        if periodo:
            query &= Q(periodo=periodo)
            
        rankings = Ranking.objects.filter(query).order_by('posicion')
        serializer = self.get_serializer(rankings, many=True)
        return Response(serializer.data)

class MensajeChatViewSet(viewsets.ModelViewSet):
    queryset = MensajeChat.objects.all()
    serializer_class = MensajeChatSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def por_sala(self, request):
        """
        Obtiene los mensajes de una sala específica
        """
        sala_id = request.query_params.get('sala_id')
        limite = request.query_params.get('limite', 50)  # Cantidad de mensajes a devolver
        
        if not sala_id:
            return Response({"error": "Se requiere el ID de la sala"}, status=status.HTTP_400_BAD_REQUEST)
            
        mensajes = MensajeChat.objects.filter(
            id_sala=sala_id
        ).order_by('-fecha_envio')[:int(limite)]
        
        serializer = self.get_serializer(mensajes, many=True)
        return Response(serializer.data)


class ApiSyncLogViewSet(viewsets.ModelViewSet):
    queryset = ApiSyncLog.objects.all()
    serializer_class = ApiSyncLogSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def ultimas_sincronizaciones(self, request):
        """
        Obtiene las últimas sincronizaciones por tipo
        """
        logs = ApiSyncLog.objects.order_by('tipo_sincronizacion', '-fecha_inicio').distinct('tipo_sincronizacion')[:10]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)