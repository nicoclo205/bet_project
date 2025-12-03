from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from datetime import timedelta
from .models import (
    ApiPais, ApiVenue, Usuario, Sala, UsuarioSala, Deporte, ApiLiga,
    ApiEquipo, ApiJugador, ApiPartido, PartidoTenis, PartidoBaloncesto,
    CarreraF1, ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    PartidoStatus, ApuestaStatus
)
from .serializers import (
    ApiPaisSerializer, ApiVenueSerializer, UsuarioSerializer, UsuarioCreateSerializer,
    SalaSerializer, UsuarioSalaSerializer, DeporteSerializer, ApiLigaSerializer,
    ApiEquipoSerializer, ApiJugadorSerializer, ApiPartidoSerializer,
    PartidoTenisSerializer, PartidoBaloncestoSerializer, CarreraF1Serializer,
    ApuestaFutbolSerializer, ApuestaTenisSerializer, ApuestaBaloncestoSerializer,
    ApuestaF1Serializer, RankingSerializer, MensajeChatSerializer,
    ApiPartidoEstadisticasSerializer, ApiPartidoEventoSerializer, ApiPartidoAlineacionSerializer
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

    # Si el token no es nuevo, lo eliminamos y creamos uno nuevo para resetear el tiempo
    if not created:
        token.delete()
        token = Token.objects.create(user=user)

    # Obtiene el perfil de Usuario asociado
    try:
        usuario = Usuario.objects.get(user=user)
    except Usuario.DoesNotExist:
        # Si no existe el perfil, puedes crearlo o manejar el error
        return Response(
            {"error": "Perfil de usuario no encontrado"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Calcula el tiempo de expiración del token
    expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
    expires_at = timezone.now() + timedelta(hours=expiration_hours)

    # Devuelve el token y datos básicos del usuario
    return Response({
        "token": token.key,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "id_usuario": usuario.id_usuario,
        "nombre_usuario": usuario.nombre_usuario,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": expiration_hours * 3600
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
def validate_token(request):
    """
    API endpoint para validar si el token es válido
    """
    return Response({
        "valid": True,
        "user_id": request.user.id,
        "username": request.user.username
    }, status=status.HTTP_200_OK)


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


# ViewSets para los modelos
class ApiPaisViewSet(viewsets.ModelViewSet):
    queryset = ApiPais.objects.all()
    serializer_class = ApiPaisSerializer


class ApiVenueViewSet(viewsets.ModelViewSet):
    queryset = ApiVenue.objects.all()
    serializer_class = ApiVenueSerializer


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

    @action(detail=False, methods=['get'])
    def miembros_sala(self, request):
        """
        Obtiene todos los miembros de una sala específica
        """
        sala_id = request.query_params.get('sala_id')
        if not sala_id:
            return Response({"error": "Se requiere el ID de la sala"}, status=status.HTTP_400_BAD_REQUEST)

        miembros = UsuarioSala.objects.filter(id_sala=sala_id)
        serializer = self.get_serializer(miembros, many=True)
        return Response(serializer.data)


class ApiLigaViewSet(viewsets.ModelViewSet):
    queryset = ApiLiga.objects.all()
    serializer_class = ApiLigaSerializer

    @action(detail=False, methods=['get'])
    def por_deporte(self, request):
        """
        Filtra ligas por deporte
        """
        deporte_id = request.query_params.get('deporte_id')
        if not deporte_id:
            return Response({"error": "Se requiere el ID del deporte"}, status=status.HTTP_400_BAD_REQUEST)

        ligas = ApiLiga.objects.filter(id_deporte=deporte_id)
        serializer = self.get_serializer(ligas, many=True)
        return Response(serializer.data)


class ApiEquipoViewSet(viewsets.ModelViewSet):
    queryset = ApiEquipo.objects.all()
    serializer_class = ApiEquipoSerializer

    @action(detail=False, methods=['get'])
    def por_deporte(self, request):
        """
        Filtra equipos por deporte
        """
        deporte_id = request.query_params.get('deporte_id')
        if not deporte_id:
            return Response({"error": "Se requiere el ID del deporte"}, status=status.HTTP_400_BAD_REQUEST)

        equipos = ApiEquipo.objects.filter(id_deporte=deporte_id)
        serializer = self.get_serializer(equipos, many=True)
        return Response(serializer.data)


class ApiJugadorViewSet(viewsets.ModelViewSet):
    queryset = ApiJugador.objects.all()
    serializer_class = ApiJugadorSerializer

    @action(detail=False, methods=['get'])
    def por_equipo(self, request):
        """
        Filtra jugadores por equipo
        """
        equipo_id = request.query_params.get('equipo_id')
        if not equipo_id:
            return Response({"error": "Se requiere el ID del equipo"}, status=status.HTTP_400_BAD_REQUEST)

        jugadores = ApiJugador.objects.filter(id_equipo=equipo_id)
        serializer = self.get_serializer(jugadores, many=True)
        return Response(serializer.data)


class ApiPartidoViewSet(viewsets.ModelViewSet):
    queryset = ApiPartido.objects.all()
    serializer_class = ApiPartidoSerializer

    @action(detail=False, methods=['get'])
    def proximos(self, request):
        """
        Obtiene los próximos partidos programados
        """
        ahora = timezone.now()
        partidos = ApiPartido.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        ).order_by('fecha')[:20]  # Limitar a 20 resultados

        serializer = self.get_serializer(partidos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_liga(self, request):
        """
        Filtra partidos por liga y opcionalmente por temporada
        """
        liga_id = request.query_params.get('liga_id')
        temporada = request.query_params.get('temporada')

        if not liga_id:
            return Response({"error": "Se requiere el ID de la liga"}, status=status.HTTP_400_BAD_REQUEST)

        query = Q(id_liga=liga_id)
        if temporada:
            query &= Q(temporada=temporada)

        partidos = ApiPartido.objects.filter(query).order_by('fecha')
        serializer = self.get_serializer(partidos, many=True)
        return Response(serializer.data)


class ApiPartidoEstadisticasViewSet(viewsets.ModelViewSet):
    queryset = ApiPartidoEstadisticas.objects.all()
    serializer_class = ApiPartidoEstadisticasSerializer

    @action(detail=False, methods=['get'])
    def por_partido(self, request):
        """
        Obtiene las estadísticas de un partido específico
        """
        partido_id = request.query_params.get('partido_id')
        if not partido_id:
            return Response({"error": "Se requiere el ID del partido"}, status=status.HTTP_400_BAD_REQUEST)

        estadisticas = ApiPartidoEstadisticas.objects.filter(id_partido=partido_id)
        serializer = self.get_serializer(estadisticas, many=True)
        return Response(serializer.data)


class ApiPartidoEventoViewSet(viewsets.ModelViewSet):
    queryset = ApiPartidoEvento.objects.all()
    serializer_class = ApiPartidoEventoSerializer

    @action(detail=False, methods=['get'])
    def por_partido(self, request):
        """
        Obtiene los eventos de un partido específico
        """
        partido_id = request.query_params.get('partido_id')
        if not partido_id:
            return Response({"error": "Se requiere el ID del partido"}, status=status.HTTP_400_BAD_REQUEST)

        eventos = ApiPartidoEvento.objects.filter(id_partido=partido_id).order_by('minuto')
        serializer = self.get_serializer(eventos, many=True)
        return Response(serializer.data)


class ApiPartidoAlineacionViewSet(viewsets.ModelViewSet):
    queryset = ApiPartidoAlineacion.objects.all()
    serializer_class = ApiPartidoAlineacionSerializer

    @action(detail=False, methods=['get'])
    def por_partido(self, request):
        """
        Obtiene las alineaciones de un partido específico
        """
        partido_id = request.query_params.get('partido_id')
        if not partido_id:
            return Response({"error": "Se requiere el ID del partido"}, status=status.HTTP_400_BAD_REQUEST)

        alineaciones = ApiPartidoAlineacion.objects.filter(id_partido=partido_id)
        serializer = self.get_serializer(alineaciones, many=True)
        return Response(serializer.data)


class PartidoTenisViewSet(viewsets.ModelViewSet):
    queryset = PartidoTenis.objects.all()
    serializer_class = PartidoTenisSerializer

    @action(detail=False, methods=['get'])
    def proximos(self, request):
        """
        Obtiene los próximos partidos de tenis programados
        """
        ahora = timezone.now()
        partidos = PartidoTenis.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        ).order_by('fecha')[:20]

        serializer = self.get_serializer(partidos, many=True)
        return Response(serializer.data)


class PartidoBaloncestoViewSet(viewsets.ModelViewSet):
    queryset = PartidoBaloncesto.objects.all()
    serializer_class = PartidoBaloncestoSerializer

    @action(detail=False, methods=['get'])
    def proximos(self, request):
        """
        Obtiene los próximos partidos de baloncesto programados
        """
        ahora = timezone.now()
        partidos = PartidoBaloncesto.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        ).order_by('fecha')[:20]

        serializer = self.get_serializer(partidos, many=True)
        return Response(serializer.data)


class CarreraF1ViewSet(viewsets.ModelViewSet):
    queryset = CarreraF1.objects.all()
    serializer_class = CarreraF1Serializer

    @action(detail=False, methods=['get'])
    def proximas(self, request):
        """
        Obtiene las próximas carreras de F1 programadas
        """
        ahora = timezone.now()
        carreras = CarreraF1.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        ).order_by('fecha')[:10]

        serializer = self.get_serializer(carreras, many=True)
        return Response(serializer.data)


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
