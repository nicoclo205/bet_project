from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Pais, Usuario, Sala, UsuarioSala, Competiciones, Equipos, Partidos, Apuestas, Ranking, MensajesChat
from .serializers import (
    PaisSerializer, UsuarioSerializer, UsuarioCreateSerializer, SalaSerializer, 
    UsuarioSalaSerializer, CompeticionesSerializer, EquiposSerializer, 
    PartidosSerializer, ApuestasSerializer, RankingSerializer, MensajesChatSerializer
)

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