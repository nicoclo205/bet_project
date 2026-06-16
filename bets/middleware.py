from django.utils import timezone
from django.conf import settings
from rest_framework.authtoken.models import Token
from datetime import timedelta
from django.http import JsonResponse
from django.core.cache import cache


class TokenExpirationMiddleware:
    """
    Valida la expiración de tokens. El resultado se cachea en Redis para
    evitar una query a MySQL en cada request autenticado.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            cache_key = f'token_valid:{token_key}'

            cached_state = cache.get(cache_key)

            if cached_state == 'expired':
                return JsonResponse(
                    {"error": "Token expirado", "code": "token_expired"},
                    status=401
                )

            if cached_state is None:
                # Cache miss: consultar la BD una sola vez
                try:
                    token = Token.objects.get(key=token_key)
                    expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
                    token_age = timezone.now() - token.created

                    if token_age > timedelta(hours=expiration_hours):
                        token.delete()
                        cache.set(cache_key, 'expired', 60)
                        return JsonResponse(
                            {"error": "Token expirado", "code": "token_expired"},
                            status=401
                        )

                    # Cachear como válido hasta 5 minutos antes de expirar
                    remaining = timedelta(hours=expiration_hours) - token_age
                    ttl = max(int(remaining.total_seconds()) - 300, 60)
                    ttl = min(ttl, 300)
                    cache.set(cache_key, 'valid', ttl)

                except Token.DoesNotExist:
                    pass  # Django lo manejará en la vista

        response = self.get_response(request)
        return response
