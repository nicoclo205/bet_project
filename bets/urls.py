from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'paises', views.PaisViewSet)
router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'salas', views.SalaViewSet)
router.register(r'usuarios-salas', views.UsuarioSalaViewSet)
router.register(r'competiciones', views.CompeticionesViewSet)
router.register(r'equipos', views.EquiposViewSet)
router.register(r'partidos', views.PartidosViewSet)
router.register(r'apuestas', views.ApuestasViewSet)
router.register(r'rankings', views.RankingViewSet)
router.register(r'mensajes', views.MensajesChatViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]