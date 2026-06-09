from django.utils import timezone
from django.conf import settings
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta


class TokenExpirationMiddleware:
    """
    Middleware para validar la expiración de tokens de autenticación
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtener el token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]

            try:
                token = Token.objects.get(key=token_key)

                # Calcular si el token ha expirado
                expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
                token_age = timezone.now() - token.created

                if token_age > timedelta(hours=expiration_hours):
                    # Token expirado, eliminarlo
                    token.delete()

                    # Devolver respuesta 401
                    return Response(
                        {"error": "Token expirado", "code": "token_expired"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except Token.DoesNotExist:
                # Token no existe, continuar (Django lo manejará)
                pass

        response = self.get_response(request)
        return response
