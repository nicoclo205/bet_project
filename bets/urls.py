from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Core data models
router.register(r'paises', views.PaisViewSet)
router.register(r'escenarios', views.EscenarioViewSet)
router.register(r'deportes', views.DeporteViewSet)

# User and room models
router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'salas', views.SalaViewSet)
router.register(r'usuarios-salas', views.UsuarioSalaViewSet)

# Sports data models
router.register(r'competencias', views.CompetenciaViewSet)
router.register(r'equipos', views.EquipoViewSet)
router.register(r'deportistas', views.DeportistaViewSet)

# Match models
router.register(r'partidos', views.PartidosViewSet)
router.register(r'partidos-futbol', views.PartidoFutbolViewSet)
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

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]