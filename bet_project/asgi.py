"""
ASGI config for bet_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')

# Inicializar Django ASGI application primero (IMPORTANTE: antes de importar routing)
django_asgi_app = get_asgi_application()

# Ahora sí importar después de inicializar Django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from bets.routing import websocket_urlpatterns

# Configurar el enrutador de protocolos para HTTP y WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
