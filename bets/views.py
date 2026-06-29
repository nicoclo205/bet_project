from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db.models import Prefetch
from django.conf import settings
from django.core.cache import cache
from datetime import timedelta
from django.http import HttpResponse
import requests
import secrets as secrets_module
from .models import (
    ApiPais, ApiVenue, Usuario, Sala, UsuarioSala, Deporte, ApiLiga,
    ApiEquipo, ApiJugador, ApiPartido, PartidoTenis, PartidoBaloncesto,
    CarreraF1, ApuestaFutbol, ApuestaTenis, ApuestaBaloncesto, ApuestaF1,
    Ranking, MensajeChat, ApiPartidoEstadisticas, ApiPartidoEvento, ApiPartidoAlineacion,
    PartidoStatus, ApuestaStatus, SalaDeporte, SalaLiga, SalaPartido, SalaNotificacion,
    RoomInvitation, LoginEvent
)
from .serializers import (
    ApiPaisSerializer, ApiVenueSerializer, UsuarioSerializer, UsuarioCreateSerializer,
    SalaSerializer, SalaCreateSerializer, SalaDetailSerializer, UsuarioSalaSerializer,
    UnirseASalaSerializer, DeporteSerializer, ApiLigaSerializer,
    ApiEquipoSerializer, ApiJugadorSerializer, ApiPartidoSerializer,
    PartidoTenisSerializer, PartidoBaloncestoSerializer, CarreraF1Serializer,
    ApuestaFutbolSerializer, ApuestaFutbolGrupoSerializer, ApuestaTenisSerializer, ApuestaBaloncestoSerializer,
    ApuestaF1Serializer, RankingSerializer, MensajeChatSerializer,
    ApiPartidoEstadisticasSerializer, ApiPartidoEventoSerializer, ApiPartidoAlineacionSerializer,
    SalaDeporteSerializer, SalaLigaSerializer, SalaPartidoSerializer, SalaNotificacionSerializer
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
        return Response(
            {"error": "Perfil de usuario no encontrado"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Verificar que el correo haya sido confirmado
    if not usuario.email_verified:
        return Response(
            {"error": "Debes verificar tu correo electrónico antes de iniciar sesión. Revisa tu bandeja de entrada."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Actualiza last_login y registra el evento de login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or \
        request.META.get('REMOTE_ADDR')
    LoginEvent.objects.create(
        usuario=usuario,
        ip_address=ip_address or None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
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
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            cache.delete(f'token_valid:{token_key}')
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
        foto_perfil = usuario.foto_perfil
    except Usuario.DoesNotExist:
        nombre_usuario = request.user.username
        id_usuario = request.user.id
        foto_perfil = None

    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
        "id_usuario": id_usuario,
        "nombre_usuario": nombre_usuario,
        "foto_perfil": foto_perfil
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

    def perform_destroy(self, instance):
        """
        Eliminar también el usuario de Django asociado
        """
        user = instance.user
        instance.delete()
        if user:
            user.delete()



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

        # Limite de salas creadas por usuario
        max_salas = getattr(settings, 'MAX_SALAS_POR_USUARIO', 5)
        salas_creadas = Sala.objects.filter(id_usuario=usuario).count()
        if salas_creadas >= max_salas:
            return Response(
                {"error": f"Has alcanzado el límite de {max_salas} salas creadas. "
                          f"Elimina una sala existente para poder crear otra."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        salas_ids = UsuarioSala.objects.filter(id_usuario=usuario).values_list('id_sala', flat=True)
        salas = Sala.objects.filter(id_sala__in=salas_ids).prefetch_related(
            Prefetch('usuariosala_set', queryset=UsuarioSala.objects.select_related('id_usuario'))
        )
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
        - modo_sala='ligas': Solo partidos de ligas habilitadas
        - modo_sala='partidos_individuales': Solo partidos agregados manualmente
        - modo_sala='mixto': Partidos de ligas habilitadas + partidos agregados manualmente
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
            try:
                sala = Sala.objects.get(id_sala=sala_id)
                modo_sala = sala.modo_sala

                # Obtener ligas habilitadas en la sala
                ligas_habilitadas = SalaLiga.objects.filter(id_sala=sala_id).values_list('id_liga', flat=True)

                # Obtener partidos agregados manualmente
                partidos_manuales = SalaPartido.objects.filter(id_sala=sala_id).values_list('id_partido', flat=True)

                # Filtrar según el modo de la sala
                if modo_sala == 'partidos_individuales':
                    if partidos_manuales.exists():
                        partidos = partidos.filter(id_partido__in=partidos_manuales)
                    else:
                        partidos = ApiPartido.objects.none()

                elif modo_sala == 'ligas':
                    if ligas_habilitadas.exists():
                        partidos = partidos.filter(id_liga__in=ligas_habilitadas)

                elif modo_sala == 'mixto':
                    if ligas_habilitadas.exists() or partidos_manuales.exists():
                        partidos = partidos.filter(
                            Q(id_liga__in=ligas_habilitadas) | Q(id_partido__in=partidos_manuales)
                        )

            except Sala.DoesNotExist:
                pass  # Si la sala no existe, mostrar todos los partidos

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


def _validar_apuesta_knockout(data):
    """
    Returns an error string if knockout-specific fields are inconsistent,
    or None if everything is valid.

    Rules:
    - Draw prediction  → tiene_tiempo_extra and tiene_penales must be True,
                          and ganador_ko must be provided.
    - Non-draw prediction → tiene_penales must not be True,
                             ganador_ko must not be set.
    """
    try:
        pred_local = int(data.get('prediccion_local', -1))
        pred_visitante = int(data.get('prediccion_visitante', -1))
    except (TypeError, ValueError):
        return None  # let the serializer handle invalid score types

    is_draw = pred_local == pred_visitante

    if is_draw:
        if not data.get('ganador_ko'):
            return (
                "Para una predicción de empate en fase eliminatoria debes "
                "seleccionar el equipo ganador por penales."
            )
        if data.get('tiene_penales') is False:
            return (
                "Una predicción de empate en fase eliminatoria siempre lleva "
                "tanda de penales."
            )
    else:
        if data.get('tiene_penales'):
            return (
                "No puede haber tanda de penales si el marcador predicho no "
                "es un empate."
            )
        if data.get('ganador_ko'):
            return (
                "El ganador por penales solo se especifica cuando la predicción "
                "del marcador es un empate."
            )
    return None


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

        # Validaciones adicionales para partidos de fase eliminatoria
        if partido.is_knockout:
            error = _validar_apuesta_knockout(mutable_data)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Si pasa las validaciones, crear la apuesta normalmente
        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Actualiza una apuesta existente validando que el partido no haya comenzado
        """
        apuesta = self.get_object()
        usuario = request.user.perfil

        # Verificar que el usuario sea el dueño de la apuesta
        if apuesta.id_usuario != usuario:
            return Response(
                {"error": "Solo puedes editar tus propias apuestas"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validar que el partido no haya comenzado
        partido = apuesta.id_partido
        ahora = timezone.now()

        if partido.fecha <= ahora:
            return Response(
                {
                    "error": "No se pueden editar apuestas para partidos que ya han comenzado o finalizado",
                    "fecha_partido": partido.fecha,
                    "fecha_actual": ahora
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que el partido no esté finalizado o en curso
        if partido.estado in [PartidoStatus.FINALIZADO, PartidoStatus.EN_CURSO]:
            return Response(
                {
                    "error": f"No se pueden editar apuestas para partidos en estado '{partido.estado}'",
                    "estado_partido": partido.estado
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validaciones adicionales para partidos de fase eliminatoria
        if partido.is_knockout:
            error = _validar_apuesta_knockout(request.data)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Elimina una apuesta validando que el partido no haya comenzado
        """
        apuesta = self.get_object()
        usuario = request.user.perfil

        # Verificar que el usuario sea el dueño de la apuesta
        if apuesta.id_usuario != usuario:
            return Response(
                {"error": "Solo puedes eliminar tus propias apuestas"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validar que el partido no haya comenzado
        partido = apuesta.id_partido
        ahora = timezone.now()

        if partido.fecha <= ahora:
            return Response(
                {
                    "error": "No se pueden eliminar apuestas para partidos que ya han comenzado o finalizado",
                    "fecha_partido": partido.fecha,
                    "fecha_actual": ahora
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que el partido no esté finalizado o en curso
        if partido.estado in [PartidoStatus.FINALIZADO, PartidoStatus.EN_CURSO]:
            return Response(
                {
                    "error": f"No se pueden eliminar apuestas para partidos en estado '{partido.estado}'",
                    "estado_partido": partido.estado
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

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

    @action(detail=False, methods=['get'])
    def otras_salas_disponibles(self, request):
        """
        Devuelve las salas del usuario (distintas a la actual) donde el mismo partido
        está disponible para apostar y el usuario todavía no ha apostado.
        Parámetros: partido_id, sala_actual_id
        """
        partido_id = request.query_params.get('partido_id')
        sala_actual_id = request.query_params.get('sala_actual_id')

        if not partido_id:
            return Response({"error": "Se requiere el ID del partido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            partido = ApiPartido.objects.get(id_partido=partido_id)
        except ApiPartido.DoesNotExist:
            return Response({"error": "El partido especificado no existe"}, status=status.HTTP_404_NOT_FOUND)

        ahora = timezone.now()
        if partido.fecha <= ahora or partido.estado in [PartidoStatus.FINALIZADO, PartidoStatus.EN_CURSO]:
            return Response([], status=status.HTTP_200_OK)

        usuario = request.user.perfil

        salas_ids = UsuarioSala.objects.filter(id_usuario=usuario).values_list('id_sala', flat=True)
        salas = Sala.objects.filter(id_sala__in=salas_ids)
        if sala_actual_id:
            salas = salas.exclude(id_sala=sala_actual_id)

        salas_con_apuesta = ApuestaFutbol.objects.filter(
            id_usuario=usuario,
            id_partido=partido
        ).values_list('id_sala', flat=True)
        salas = salas.exclude(id_sala__in=salas_con_apuesta)

        salas_disponibles = []
        for sala in salas:
            modo_sala = sala.modo_sala
            match_disponible = False

            if modo_sala == 'partidos_individuales':
                match_disponible = SalaPartido.objects.filter(
                    id_sala=sala, id_partido=partido
                ).exists()

            elif modo_sala == 'ligas':
                ligas_habilitadas = list(SalaLiga.objects.filter(
                    id_sala=sala
                ).values_list('id_liga', flat=True))
                match_disponible = partido.id_liga_id in set(ligas_habilitadas) if ligas_habilitadas else True

            elif modo_sala == 'mixto':
                ligas_habilitadas = list(SalaLiga.objects.filter(
                    id_sala=sala
                ).values_list('id_liga', flat=True))
                partidos_manuales = list(SalaPartido.objects.filter(
                    id_sala=sala
                ).values_list('id_partido', flat=True))
                if ligas_habilitadas or partidos_manuales:
                    match_disponible = (
                        partido.id_liga_id in set(ligas_habilitadas) or
                        partido.id_partido in set(partidos_manuales)
                    )
                else:
                    match_disponible = True

            if match_disponible:
                salas_disponibles.append(sala)

        serializer = SalaSerializer(salas_disponibles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_sala(self, request):
        """
        Todas las apuestas de una sala con detalles del partido.
        Usado por la vista de predicciones del grupo.
        """
        sala_id = request.query_params.get('sala_id')
        if not sala_id:
            return Response({"error": "Se requiere sala_id"}, status=status.HTTP_400_BAD_REQUEST)

        apuestas = ApuestaFutbol.objects.filter(
            id_sala=sala_id
        ).select_related(
            'id_usuario',
            'id_partido',
            'id_partido__equipo_local',
            'id_partido__equipo_visitante',
        ).order_by('id_partido__fecha', 'id_usuario__nombre_usuario')

        serializer = ApuestaFutbolGrupoSerializer(apuestas, many=True)
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
        Obtiene el ranking actual de una sala. Usa una sola query de agregación
        en lugar de un query por cada miembro.
        """
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

        miembros = UsuarioSala.objects.filter(id_sala=sala).select_related('id_usuario')
        usuario_ids = [m.id_usuario_id for m in miembros]

        # Una sola query GROUP BY en lugar de N queries (una por miembro)
        stats_qs = ApuestaFutbol.objects.filter(
            id_sala=sala,
            id_usuario__in=usuario_ids,
        ).values('id_usuario').annotate(
            total_puntos=Sum('puntos_ganados'),
            total_apuestas=Count('id_apuesta'),
            apuestas_ganadas=Count('id_apuesta', filter=Q(estado=ApuestaStatus.GANADA)),
            apuestas_perdidas=Count('id_apuesta', filter=Q(estado=ApuestaStatus.PERDIDA)),
        )
        stats_dict = {s['id_usuario']: s for s in stats_qs}

        ranking_data = []
        for miembro in miembros:
            usuario = miembro.id_usuario
            s = stats_dict.get(usuario.id_usuario, {})
            total = s.get('total_apuestas') or 0
            ganadas = s.get('apuestas_ganadas') or 0
            perdidas = s.get('apuestas_perdidas') or 0
            puntos = s.get('total_puntos') or 0

            ranking_data.append({
                'usuario': {
                    'id_usuario': usuario.id_usuario,
                    'nombre_usuario': usuario.nombre_usuario,
                    'nombre': usuario.nombre,
                    'apellido': usuario.apellido,
                    'foto_perfil': usuario.foto_perfil,
                },
                'puntos': puntos,
                'total_apuestas': total,
                'apuestas_ganadas': ganadas,
                'apuestas_perdidas': perdidas,
                'efectividad': round((ganadas / total * 100) if total > 0 else 0, 2),
            })

        ranking_data.sort(key=lambda x: x['puntos'], reverse=True)
        for idx, item in enumerate(ranking_data, start=1):
            item['posicion'] = idx

        return Response({
            'sala': {
                'id_sala': sala.id_sala,
                'nombre': sala.nombre,
                'descripcion': sala.descripcion,
            },
            'ranking': ranking_data,
            'total_participantes': len(ranking_data),
        })


class MensajeChatViewSet(viewsets.ModelViewSet):
    queryset = MensajeChat.objects.all()
    serializer_class = MensajeChatSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        mensaje = serializer.save(id_usuario=self.request.user)
        sala = mensaje.id_sala
        usuario = self.request.user
        # One chat notification per sala per 15 minutes to avoid spamming
        quince_min_atras = timezone.now() - timedelta(minutes=15)
        ya_existe = SalaNotificacion.objects.filter(
            id_sala=sala,
            tipo='nuevo_mensaje_chat',
            fecha__gte=quince_min_atras
        ).exists()
        if not ya_existe:
            SalaNotificacion.objects.create(
                id_sala=sala,
                tipo='nuevo_mensaje_chat',
                mensaje=f'\U0001f4ac {usuario.nombre_usuario} sent a message in {sala.nombre}',
                icono='\U0001f4ac',
                color='text-blue-400',
                usuario_relacionado=usuario,
            )

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


class SalaNotificacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar notificaciones/avisos importantes de una sala.
    """
    queryset = SalaNotificacion.objects.all()
    serializer_class = SalaNotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar por sala si se proporciona sala_id"""
        queryset = super().get_queryset()
        sala_id = self.request.query_params.get('sala_id')
        if sala_id:
            queryset = queryset.filter(id_sala=sala_id)
        return queryset.select_related('id_sala', 'usuario_relacionado', 'partido_relacionado')

    def create(self, request, *args, **kwargs):
        """Crear notificación personalizada (solo admin)"""
        sala_id = request.data.get('id_sala')
        try:
            sala = Sala.objects.get(id_sala=sala_id)
            if sala.id_usuario.user != request.user:
                return Response(
                    {"error": "Solo el administrador de la sala puede crear notificaciones"},
                    status=status.HTTP_403_FORBIDDEN
                )

            return super().create(request, *args, **kwargs)

        except Sala.DoesNotExist:
            return Response(
                {"error": "La sala especificada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        """Solo el admin de la sala puede eliminar notificaciones"""
        instance = self.get_object()
        if instance.id_sala.id_usuario.user != request.user:
            return Response(
                {"error": "Solo el administrador de la sala puede eliminar notificaciones"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

# ─── Room Invitation Views ──────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_to_room(request, sala_id):
    """
    POST /api/salas/<sala_id>/invite/
    Body: { "email": "..." }
    Only the room admin can send invitations.
    """
    try:
        sala = Sala.objects.get(id_sala=sala_id)
    except Sala.DoesNotExist:
        return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

    # Permission: only the room owner
    try:
        usuario = Usuario.objects.get(user=request.user)
    except Usuario.DoesNotExist:
        return Response({"error": "User profile not found"}, status=status.HTTP_403_FORBIDDEN)

    if sala.id_usuario != usuario:
        return Response({"error": "Only the room admin can send invitations"}, status=status.HTTP_403_FORBIDDEN)

    invited_email = request.data.get('email', '').strip().lower()
    if not invited_email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Check if already a member
    if Usuario.objects.filter(correo=invited_email).exists():
        existing_user = Usuario.objects.get(correo=invited_email)
        if UsuarioSala.objects.filter(id_usuario=existing_user, id_sala=sala).exists():
            return Response({"error": "This user is already a member of the room"}, status=status.HTTP_400_BAD_REQUEST)

    # Invalidate any previous unused invite for the same email+room
    RoomInvitation.objects.filter(sala=sala, invited_email=invited_email, is_used=False).update(is_used=True)

    # Create new invitation token
    token = secrets_module.token_urlsafe(32)
    invitation = RoomInvitation.objects.create(
        sala=sala,
        invited_by=usuario,
        invited_email=invited_email,
        token=token,
    )

    # Send email
    from .email_service import send_room_invitation_email
    try:
        send_room_invitation_email(
            invited_email=invited_email,
            invite_token=token,
            room_name=sala.nombre,
            inviter_name=usuario.nombre_usuario,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send invite email: {e}")
        return Response({"error": "Failed to send invitation email. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"success": True, "message": f"Invitation sent to {invited_email}"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def validate_invite_token(request):
    """
    GET /api/invitations/validate/?token=<token>
    Returns room info if the token is valid (used on the register page to show context).
    """
    token = request.query_params.get('token', '').strip()
    if not token:
        return Response({"valid": False, "error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        invitation = RoomInvitation.objects.select_related('sala').get(token=token, is_used=False)
    except RoomInvitation.DoesNotExist:
        return Response({"valid": False, "error": "Invalid or expired invitation"}, status=status.HTTP_404_NOT_FOUND)

    if not invitation.is_valid():
        return Response({"valid": False, "error": "Invitation has expired"}, status=status.HTTP_410_GONE)

    return Response({
        "valid": True,
        "room_name": invitation.sala.nombre,
        "invited_email": invitation.invited_email,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_invite(request):
    """
    POST /api/invitations/accept/
    Body: { "token": "...", "email": "..." }
    Called right after registration to auto-join the invited room.
    No auth required — the token itself is the proof of authorization.
    """
    token = request.data.get('token', '').strip()
    email = request.data.get('email', '').strip().lower()

    if not token or not email:
        return Response({"error": "token and email are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        invitation = RoomInvitation.objects.select_related('sala').get(token=token, is_used=False)
    except RoomInvitation.DoesNotExist:
        return Response({"error": "Invalid or already used invitation"}, status=status.HTTP_404_NOT_FOUND)

    if not invitation.is_valid():
        return Response({"error": "Invitation has expired"}, status=status.HTTP_410_GONE)

    try:
        usuario = Usuario.objects.get(correo=email)
    except Usuario.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    UsuarioSala.objects.get_or_create(
        id_usuario=usuario,
        id_sala=invitation.sala,
        defaults={'rol': 'participante'}
    )

    invitation.is_used = True
    invitation.used_at = timezone.now()
    invitation.save()

    return Response({"success": True, "room_name": invitation.sala.nombre}, status=status.HTTP_200_OK)


# ─── Notification Views ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_notificaciones(request):
    """
    GET /api/notificaciones/mias/
    Devuelve notificaciones recientes de todas las salas del usuario y los
    conteos de no leídas. Crea recordatorios de partidos próximos (12h) de
    forma lazy pero con queries batched para evitar N+1.
    """
    from datetime import timedelta as td
    from collections import defaultdict
    usuario = request.user.perfil
    ahora = timezone.now()
    ventana = ahora + td(hours=12)

    memberships = list(UsuarioSala.objects.filter(id_usuario=usuario).select_related('id_sala'))
    if not memberships:
        return Response({'total_no_leidas': 0, 'salas': []})

    sala_ids = [m.id_sala_id for m in memberships]

    # ── Recordatorios de partidos próximos (todas las salas de una vez) ──
    partidos_proximos = list(ApiPartido.objects.filter(
        fecha__gte=ahora,
        fecha__lte=ventana,
        estado='programado',
    ).select_related('equipo_local', 'equipo_visitante'))

    if partidos_proximos:
        partido_ids = [p.id_partido for p in partidos_proximos]

        # Qué liga pertenece a qué sala (1 query)
        sala_liga_set = set(
            SalaLiga.objects.filter(id_sala__in=sala_ids)
            .values_list('id_sala_id', 'id_liga_id')
        )
        # Qué partido manual pertenece a qué sala (1 query)
        sala_partido_set = set(
            SalaPartido.objects.filter(id_sala__in=sala_ids, id_partido__in=partido_ids)
            .values_list('id_sala_id', 'id_partido_id')
        )
        # Recordatorios ya creados hoy (1 query)
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        existing_reminders = set(
            SalaNotificacion.objects.filter(
                id_sala__in=sala_ids,
                tipo='recordatorio_partido',
                partido_relacionado__in=partido_ids,
                fecha__gte=hoy_inicio,
            ).values_list('id_sala_id', 'partido_relacionado_id')
        )

        # Construir las notificaciones faltantes en memoria, luego bulk_create
        nuevas = []
        for sala_id in sala_ids:
            for partido in partidos_proximos:
                pid = partido.id_partido
                liga_id = partido.id_liga_id
                pertenece = (sala_id, liga_id) in sala_liga_set or (sala_id, pid) in sala_partido_set
                if not pertenece or (sala_id, pid) in existing_reminders:
                    continue
                minutos = int((partido.fecha - ahora).total_seconds() / 60)
                tiempo_texto = f"{minutos // 60}h" if minutos >= 60 else f"{minutos}min"
                local = partido.equipo_local.nombre if partido.equipo_local else '?'
                visitante = partido.equipo_visitante.nombre if partido.equipo_visitante else '?'
                nuevas.append(SalaNotificacion(
                    id_sala_id=sala_id,
                    tipo='recordatorio_partido',
                    mensaje=f"⚽ {local} vs {visitante} empieza en {tiempo_texto} — ¡no olvides apostar!",
                    icono='⏰',
                    color='text-yellow-400',
                    partido_relacionado_id=pid,
                ))
        if nuevas:
            SalaNotificacion.objects.bulk_create(nuevas)

    # ── Todas las notificaciones de todas las salas en 1 query ───────────
    all_notifs = (
        SalaNotificacion.objects
        .filter(id_sala__in=sala_ids)
        .select_related('usuario_relacionado', 'partido_relacionado')
        .order_by('id_sala_id', '-fecha')
    )
    notif_por_sala = defaultdict(list)
    for n in all_notifs:
        bucket = notif_por_sala[n.id_sala_id]
        if len(bucket) < 10:
            bucket.append(n)

    # ── Construir respuesta en memoria ────────────────────────────────────
    resultado = []
    total_no_leidas = 0

    for membership in memberships:
        sala = membership.id_sala
        ultima_vista = membership.ultima_notificacion_vista
        notificaciones = notif_por_sala[sala.id_sala]

        no_leidas = 0
        notifs_data = []
        for n in notificaciones:
            leida = ultima_vista is not None and n.fecha <= ultima_vista
            if not leida:
                no_leidas += 1
            notifs_data.append({
                'id': n.id_notificacion,
                'tipo': n.tipo,
                'mensaje': n.mensaje,
                'icono': n.icono,
                'color': n.color,
                'fecha': n.fecha.isoformat(),
                'leida': leida,
                'sala_id': sala.id_sala,
                'sala_nombre': sala.nombre,
            })

        total_no_leidas += no_leidas
        resultado.append({
            'sala_id': sala.id_sala,
            'sala_nombre': sala.nombre,
            'no_leidas': no_leidas,
            'notificaciones': notifs_data,
        })

    return Response({'total_no_leidas': total_no_leidas, 'salas': resultado})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_notificaciones_vistas(request):
    """
    POST /api/notificaciones/marcar-vistas/
    Body: { "sala_id": 2 }  (optional - if omitted marks all rooms)
    """
    usuario = request.user.perfil
    sala_id = request.data.get('sala_id')
    ahora = timezone.now()

    if sala_id:
        UsuarioSala.objects.filter(
            id_usuario=usuario,
            id_sala_id=sala_id
        ).update(ultima_notificacion_vista=ahora)
    else:
        UsuarioSala.objects.filter(
            id_usuario=usuario
        ).update(ultima_notificacion_vista=ahora)

    return Response({'success': True, 'timestamp': ahora.isoformat()})
