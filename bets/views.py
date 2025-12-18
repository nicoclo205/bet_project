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
from django.http import HttpResponse
import requests
from .models import (
    ApiPais, ApiVenue, Usuario, Sala, UsuarioSala, Deporte, ApiLiga,
    ApiEquipo, ApiJugador, ApiPartido, PartidoTenis, PartidoBaloncesto,
    CarreraF1, ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    PartidoStatus, ApuestaStatus, SalaDeporte, SalaLiga, SalaPartido
)
from .serializers import (
    ApiPaisSerializer, ApiVenueSerializer, UsuarioSerializer, UsuarioCreateSerializer,
    SalaSerializer, SalaCreateSerializer, SalaDetailSerializer, UsuarioSalaSerializer,
    UnirseASalaSerializer, DeporteSerializer, ApiLigaSerializer,
    ApiEquipoSerializer, ApiJugadorSerializer, ApiPartidoSerializer,
    PartidoTenisSerializer, PartidoBaloncestoSerializer, CarreraF1Serializer,
    ApuestaFutbolSerializer, ApuestaTenisSerializer, ApuestaBaloncestoSerializer,
    ApuestaF1Serializer, RankingSerializer, MensajeChatSerializer,
    ApiPartidoEstadisticasSerializer, ApiPartidoEventoSerializer, ApiPartidoAlineacionSerializer,
    SalaDeporteSerializer, SalaLigaSerializer, SalaPartidoSerializer
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



#gestión de salas
class SalaViewSet(viewsets.ModelViewSet):
    queryset = Sala.objects.all()
    serializer_class = SalaSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Usar diferentes serializers según la acción"""
        if self.action == 'create':
            return SalaCreateSerializer
        elif self.action == 'retrieve':
            return SalaDetailSerializer
        return SalaSerializer

    def create(self, request, *args, **kwargs):
        """
        Crear sala y auto-agregar al creador como admin
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Asignar el usuario autenticado como creador
        usuario = request.user.perfil
        sala = serializer.save(id_usuario=usuario)
        
        # Generar código único para la sala (si no existe)
        if not sala.codigo_sala:
            import uuid
            sala.codigo_sala = str(uuid.uuid4())[:8].upper()
            sala.save()
        
        # Auto-agregar al creador como admin en UsuarioSala
        UsuarioSala.objects.create(
            id_usuario=usuario,
            id_sala=sala,
            rol='admin'
        )
        
        # Retornar la sala creada con todos los detalles
        response_serializer = SalaDetailSerializer(sala)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Permitir editar solo al creador de la sala
        """
        sala = self.get_object()
        usuario = request.user.perfil
        
        # Verificar que el usuario sea el creador
        if sala.id_usuario != usuario:
            return Response(
                {"error": "Solo el creador puede editar la sala"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Permitir eliminar solo al creador de la sala
        """
        sala = self.get_object()
        usuario = request.user.perfil
        
        # Verificar que el usuario sea el creador
        if sala.id_usuario != usuario:
            return Response(
                {"error": "Solo el creador puede eliminar la sala"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def mis_salas(self, request):
        """
        Devuelve las salas a las que pertenece el usuario autenticado
        """
        usuario = request.user.perfil
        
        # Obtener salas donde el usuario es miembro (vía UsuarioSala)
        salas_ids = UsuarioSala.objects.filter(id_usuario=usuario).values_list('id_sala', flat=True)
        salas = Sala.objects.filter(id_sala__in=salas_ids)
        
        # Serializar los resultados
        serializer = SalaDetailSerializer(salas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unirse(self, request, pk=None):
        """
        Permite a un usuario unirse a una sala usando su código
        """
        codigo = request.data.get('codigo_sala')
        if not codigo:
            return Response(
                {"error": "Se requiere el código de sala"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sala = Sala.objects.get(codigo_sala=codigo)
        except Sala.DoesNotExist:
            return Response(
                {"error": "Código de sala inválido"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        usuario = request.user.perfil

        # Verificar si ya es miembro
        if UsuarioSala.objects.filter(id_usuario=usuario, id_sala=sala).exists():
            return Response(
                {"error": "Ya eres miembro de esta sala"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear la relación UsuarioSala con rol 'participante'
        UsuarioSala.objects.create(
            id_usuario=usuario, 
            id_sala=sala,
            rol='participante'  
        )

        response_data = {
            "message": f"Te has unido a la sala '{sala.nombre}'",
            "sala": SalaDetailSerializer(sala).data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def salir(self, request, pk=None):
        """
        Permite a un usuario salir de una sala
        """
        sala = self.get_object()
        usuario = request.user.perfil
        
        # Verificar que no sea el creador
        if sala.id_usuario == usuario:
            return Response(
                {"error": "El creador no puede salir de su propia sala. Debe eliminarla."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usuario_sala = UsuarioSala.objects.get(id_usuario=usuario, id_sala=sala)
            usuario_sala.delete()
            return Response(
                {"message": f"Has salido de la sala '{sala.nombre}'"}, 
                status=status.HTTP_200_OK
            )
        except UsuarioSala.DoesNotExist:
            return Response(
                {"error": "No eres miembro de esta sala"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def miembros(self, request, pk=None):
        """
        Ver todos los miembros de una sala
        """
        sala = self.get_object()
        usuario = request.user.perfil
        
        # Verificar que el usuario sea miembro de la sala
        if not UsuarioSala.objects.filter(id_usuario=usuario, id_sala=sala).exists():
            return Response(
                {"error": "No tienes acceso a esta sala"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        miembros = UsuarioSala.objects.filter(id_sala=sala)
        serializer = UsuarioSalaSerializer(miembros, many=True)
        return Response(serializer.data)

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
        Obtiene los próximos partidos programados.
        Si se proporciona sala_id, filtra según la configuración de la sala:
        - Partidos de deportes habilitados
        - Partidos de ligas habilitadas
        - Partidos agregados manualmente por el admin
        """
        ahora = timezone.now()
        sala_id = request.query_params.get('sala_id')

        # Query base: partidos próximos programados
        partidos = ApiPartido.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        )

        # Si se especifica una sala, filtrar según configuración
        if sala_id:
            # Obtener ligas habilitadas en la sala
            ligas_habilitadas = SalaLiga.objects.filter(id_sala=sala_id).values_list('id_liga', flat=True)

            # Obtener partidos agregados manualmente
            partidos_manuales = SalaPartido.objects.filter(id_sala=sala_id).values_list('id_partido', flat=True)

            # Si hay configuración, filtrar
            if ligas_habilitadas.exists() or partidos_manuales.exists():
                # Partidos que pertenecen a ligas habilitadas O fueron agregados manualmente
                partidos = partidos.filter(
                    Q(id_liga__in=ligas_habilitadas) | Q(id_partido__in=partidos_manuales)
                )
            # Si no hay configuración, mostrar todos los partidos (sala sin configurar)

        partidos = partidos.order_by('fecha')[:50]  # Limitar a 50 resultados
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
    
    @action(detail=False, methods=['get'])
    def por_deporte(self, request):
        """
        Filtra partidos por deporte (a través de las ligas)
        """
        deporte_id = request.query_params.get('deporte_id')
        if not deporte_id:
            return Response({"error": "Se requiere el ID del deporte"}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar las ligas que pertenecen a ese deporte
        ligas = ApiLiga.objects.filter(id_deporte=deporte_id).values_list('id_liga', flat=True)

        # Buscar los partidos de esas ligas
        partidos = ApiPartido.objects.filter(id_liga__in=ligas).order_by('fecha')

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

    def create(self, request, *args, **kwargs):
        """
        Crea una nueva apuesta validando que el partido no haya comenzado
        """
        # Obtener el ID del partido del request
        partido_id = request.data.get('id_partido')

        if not partido_id:
            return Response(
                {"error": "Se requiere el ID del partido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Buscar el partido
            partido = ApiPartido.objects.get(id_partido=partido_id)

            # Validar que el partido no haya comenzado
            ahora = timezone.now()
            if partido.fecha <= ahora:
                return Response(
                    {
                        "error": "No se pueden realizar apuestas para partidos que ya han comenzado o finalizado",
                        "fecha_partido": partido.fecha,
                        "fecha_actual": ahora
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validar que el partido no esté finalizado o en curso
            if partido.estado in [PartidoStatus.FINALIZADO, PartidoStatus.EN_CURSO]:
                return Response(
                    {
                        "error": f"No se pueden realizar apuestas para partidos en estado '{partido.estado}'",
                        "estado_partido": partido.estado
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except ApiPartido.DoesNotExist:
            return Response(
                {"error": "El partido especificado no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Asignar el usuario autenticado a la apuesta
        mutable_data = request.data.copy()
        mutable_data['id_usuario'] = request.user.perfil.id_usuario

        # Si pasa las validaciones, crear la apuesta normalmente
        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

    @action(detail=False, methods=['get'])
    def actual(self, request):
        """
        Obtiene el ranking actual de una sala basado en los puntos totales
        de todas las apuestas ganadas (no usa la tabla Ranking)
        """
        from django.db.models import Sum, Count

        sala_id = request.query_params.get('sala_id')

        if not sala_id:
            return Response(
                {"error": "Se requiere el ID de la sala"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sala = Sala.objects.get(id_sala=sala_id)
        except Sala.DoesNotExist:
            return Response(
                {"error": "La sala especificada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Obtener miembros de la sala con sus estadísticas
        miembros = UsuarioSala.objects.filter(id_sala=sala).select_related('id_usuario')

        ranking_data = []
        for miembro in miembros:
            usuario = miembro.id_usuario

            # Calcular estadísticas del usuario en esta sala
            apuestas_stats = ApuestaFutbol.objects.filter(
                id_usuario=usuario,
                id_sala=sala
            ).aggregate(
                total_puntos=Sum('puntos_ganados'),
                total_apuestas=Count('id_apuesta'),
                apuestas_ganadas=Count('id_apuesta', filter=Q(estado=ApuestaStatus.GANADA)),
                apuestas_perdidas=Count('id_apuesta', filter=Q(estado=ApuestaStatus.PERDIDA))
            )

            ranking_data.append({
                'usuario': {
                    'id_usuario': usuario.id_usuario,
                    'nombre_usuario': usuario.nombre_usuario,
                    'nombre': usuario.nombre,
                    'apellido': usuario.apellido,
                    'foto_perfil': usuario.foto_perfil,
                },
                'puntos': apuestas_stats['total_puntos'] or 0,
                'total_apuestas': apuestas_stats['total_apuestas'],
                'apuestas_ganadas': apuestas_stats['apuestas_ganadas'],
                'apuestas_perdidas': apuestas_stats['apuestas_perdidas'],
                'efectividad': round(
                    (apuestas_stats['apuestas_ganadas'] / apuestas_stats['total_apuestas'] * 100)
                    if apuestas_stats['total_apuestas'] > 0 else 0,
                    2
                )
            })

        # Ordenar por puntos descendente
        ranking_data.sort(key=lambda x: x['puntos'], reverse=True)

        # Asignar posiciones
        for idx, item in enumerate(ranking_data, start=1):
            item['posicion'] = idx

        return Response({
            'sala': {
                'id_sala': sala.id_sala,
                'nombre': sala.nombre,
                'descripcion': sala.descripcion,
            },
            'ranking': ranking_data,
            'total_participantes': len(ranking_data)
        })


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


# Proxy para imágenes de SofaScore (evita problemas de CORS)
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso sin autenticación para las imágenes
def sofascore_image_proxy(request, team_id):
    """
    Proxy para servir imágenes de equipos desde SofaScore
    Evita problemas de CORS en el navegador
    """
    try:
        # URL de la imagen en SofaScore
        image_url = f'https://api.sofascore.app/api/v1/team/{team_id}/image'

        # Hacer la petición al servidor de SofaScore
        response = requests.get(image_url, timeout=5)

        # Si la petición fue exitosa, devolver la imagen
        if response.status_code == 200:
            # Crear respuesta HTTP con la imagen
            return HttpResponse(
                response.content,
                content_type=response.headers.get('Content-Type', 'image/png')
            )
        else:
            # Si falla, devolver error 404
            return HttpResponse(status=404)

    except Exception as e:
        # En caso de error, devolver 404
        print(f"Error al obtener imagen de SofaScore: {e}")
        return HttpResponse(status=404)


# =============================================================================
# VIEWSETS DE CONFIGURACIÓN DE SALA
# =============================================================================

class SalaDeporteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar deportes habilitados en una sala.
    Solo el administrador de la sala puede agregar/quitar deportes.
    """
    queryset = SalaDeporte.objects.all()
    serializer_class = SalaDeporteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar por sala si se proporciona sala_id"""
        queryset = super().get_queryset()
        sala_id = self.request.query_params.get('sala_id')
        if sala_id:
            queryset = queryset.filter(id_sala=sala_id)
        return queryset

    def create(self, request, *args, **kwargs):
        """Solo el admin de la sala puede agregar deportes"""
        sala_id = request.data.get('id_sala')
        try:
            sala = Sala.objects.get(id_sala=sala_id)
            # Verificar que el usuario es el creador de la sala
            if sala.id_usuario.user != request.user:
                return Response(
                    {"error": "Solo el administrador de la sala puede agregar deportes"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Sala.DoesNotExist:
            return Response(
                {"error": "La sala especificada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Solo el admin de la sala puede quitar deportes"""
        instance = self.get_object()
        if instance.id_sala.id_usuario.user != request.user:
            return Response(
                {"error": "Solo el administrador de la sala puede quitar deportes"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class SalaLigaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ligas/torneos habilitados en una sala.
    Solo el administrador de la sala puede agregar/quitar ligas.
    """
    queryset = SalaLiga.objects.all()
    serializer_class = SalaLigaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar por sala si se proporciona sala_id"""
        queryset = super().get_queryset()
        sala_id = self.request.query_params.get('sala_id')
        if sala_id:
            queryset = queryset.filter(id_sala=sala_id)
        return queryset.select_related('id_liga', 'id_liga__id_pais', 'id_liga__id_deporte')

    def create(self, request, *args, **kwargs):
        """Solo el admin de la sala puede agregar ligas"""
        sala_id = request.data.get('id_sala')
        try:
            sala = Sala.objects.get(id_sala=sala_id)
            if sala.id_usuario.user != request.user:
                return Response(
                    {"error": "Solo el administrador de la sala puede agregar ligas"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Sala.DoesNotExist:
            return Response(
                {"error": "La sala especificada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Solo el admin de la sala puede quitar ligas"""
        instance = self.get_object()
        if instance.id_sala.id_usuario.user != request.user:
            return Response(
                {"error": "Solo el administrador de la sala puede quitar ligas"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """
        Obtiene ligas disponibles para agregar a una sala (aún no agregadas)
        """
        sala_id = request.query_params.get('sala_id')
        if not sala_id:
            return Response(
                {"error": "Se requiere el parámetro sala_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ligas ya agregadas a la sala
        ligas_en_sala = SalaLiga.objects.filter(id_sala=sala_id).values_list('id_liga', flat=True)

        # Ligas disponibles (no agregadas)
        ligas_disponibles = ApiLiga.objects.exclude(id_liga__in=ligas_en_sala)

        serializer = ApiLigaSerializer(ligas_disponibles, many=True)
        return Response(serializer.data)


class SalaPartidoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar partidos individuales habilitados en una sala.
    Solo el administrador de la sala puede agregar/quitar partidos.
    """
    queryset = SalaPartido.objects.all()
    serializer_class = SalaPartidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar por sala si se proporciona sala_id"""
        queryset = super().get_queryset()
        sala_id = self.request.query_params.get('sala_id')
        if sala_id:
            queryset = queryset.filter(id_sala=sala_id)
        return queryset.select_related('id_partido', 'id_partido__equipo_local', 'id_partido__equipo_visitante')

    def create(self, request, *args, **kwargs):
        """Solo el admin de la sala puede agregar partidos"""
        sala_id = request.data.get('id_sala')
        try:
            sala = Sala.objects.get(id_sala=sala_id)
            if sala.id_usuario.user != request.user:
                return Response(
                    {"error": "Solo el administrador de la sala puede agregar partidos"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Asignar el usuario que agregó el partido
            mutable_data = request.data.copy()
            mutable_data['agregado_por'] = request.user.perfil.id_usuario

            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Sala.DoesNotExist:
            return Response(
                {"error": "La sala especificada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        """Solo el admin de la sala puede quitar partidos"""
        instance = self.get_object()
        if instance.id_sala.id_usuario.user != request.user:
            return Response(
                {"error": "Solo el administrador de la sala puede quitar partidos"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """
        Obtiene partidos disponibles para agregar manualmente a una sala
        (partidos próximos que aún no están en la sala)
        """
        sala_id = request.query_params.get('sala_id')
        if not sala_id:
            return Response(
                {"error": "Se requiere el parámetro sala_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Partidos ya agregados a la sala
        partidos_en_sala = SalaPartido.objects.filter(id_sala=sala_id).values_list('id_partido', flat=True)

        # Partidos próximos disponibles (no agregados manualmente)
        ahora = timezone.now()
        partidos_disponibles = ApiPartido.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        ).exclude(id_partido__in=partidos_en_sala).order_by('fecha')[:50]

        serializer = ApiPartidoSerializer(partidos_disponibles, many=True)
        return Response(serializer.data)
