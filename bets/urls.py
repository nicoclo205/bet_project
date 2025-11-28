from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Core data models
router.register(r'paises', views.ApiPaisViewSet)
router.register(r'venues', views.ApiVenueViewSet)
router.register(r'deportes', views.DeporteViewSet)

# User and room models
router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'salas', views.SalaViewSet)
router.register(r'usuarios-salas', views.UsuarioSalaViewSet)

# Sports data models
router.register(r'ligas', views.ApiLigaViewSet)
router.register(r'equipos', views.ApiEquipoViewSet)
router.register(r'jugadores', views.ApiJugadorViewSet)

# Match models
router.register(r'partidos', views.ApiPartidoViewSet)
router.register(r'partidos-estadisticas', views.ApiPartidoEstadisticasViewSet)
router.register(r'partidos-eventos', views.ApiPartidoEventoViewSet)
router.register(r'partidos-alineaciones', views.ApiPartidoAlineacionViewSet)
router.register(r'partidos-tenis', views.PartidoTenisViewSet)
router.register(r'partidos-baloncesto', views.PartidoBaloncestoViewSet)
router.register(r'carreras-f1', views.CarreraF1ViewSet)

# Bet models
router.register(r'apuestas-futbol', views.ApuestaFutbolViewSet)
router.register(r'apuestas-tenis', views.ApuestaTenisViewSet)
router.register(r'apuestas-baloncesto', views.ApuestaBaloncestoViewSet)
router.register(r'apuestas-f1', views.ApuestaF1ViewSet)

# Social models
router.register(r'rankings', views.RankingViewSet)
router.register(r'mensajes-chat', views.MensajeChatViewSet)

# API synchronization logs
router.register(r'sync-logs', views.ApiSyncLogViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    # Authentication endpoints
    path('api/login', views.login_view, name='login'),
    path('api/logout', views.logout_view, name='logout'),
    path('api/usuario/me', views.usuario_me, name='usuario_me'),
]