from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import auth_views

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

# Room configuration models
router.register(r'sala-deportes', views.SalaDeporteViewSet)
router.register(r'sala-ligas', views.SalaLigaViewSet)
router.register(r'sala-partidos', views.SalaPartidoViewSet)
router.register(r'sala-notificaciones', views.SalaNotificacionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    # Authentication endpoints
    path('api/login', views.login_view, name='login'),
    path('api/logout', views.logout_view, name='logout'),
    path('api/validate-token', views.validate_token, name='validate_token'),
    path('api/usuario/me', views.usuario_me, name='usuario_me'),
    # Email verification endpoints
    path('api/verify-email', auth_views.verify_email, name='verify_email'),
    path('api/resend-verification', auth_views.resend_verification_email, name='resend_verification'),
    # Password reset endpoints
    path('api/request-password-reset', auth_views.request_password_reset, name='request_password_reset'),
    path('api/reset-password', auth_views.reset_password, name='reset_password'),
    path('api/validate-reset-token', auth_views.validate_reset_token, name='validate_reset_token'),
    # Image proxy
    path('api/proxy/sofascore/team/<int:team_id>/image', views.sofascore_image_proxy, name='sofascore_image_proxy'),
]