import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import MensajeChat, Sala, Usuario

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Se ejecuta cuando un cliente se conecta al WebSocket"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Obtener token del query string
        query_string = self.scope['query_string'].decode()
        token = None
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]

        # Validar token y usuario
        self.user = await self.get_user_from_token(token)
        if not self.user:
            await self.close()
            return

        # Validar que el usuario pertenece a la sala
        if not await self.user_in_room(self.user, self.room_id):
            await self.close()
            return

        # Unirse al grupo de la sala
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Enviar mensajes recientes al conectarse
        recent_messages = await self.get_recent_messages(self.room_id)
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': recent_messages
        }))

    async def disconnect(self, close_code):
        """Se ejecuta cuando un cliente se desconecta"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Se ejecuta cuando se recibe un mensaje del cliente"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')

            if message_type == 'message':
                contenido = data['contenido']

                # Guardar mensaje en la base de datos
                mensaje = await self.save_message(
                    self.room_id,
                    self.user.id_usuario,
                    contenido
                )

                # Enviar mensaje a todos los miembros de la sala
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id_mensaje': mensaje['id_mensaje'],
                            'contenido': mensaje['contenido'],
                            'fecha_envio': mensaje['fecha_envio'],
                            'usuario': mensaje['usuario'],
                        }
                    }
                )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def chat_message(self, event):
        """Envía el mensaje al WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Obtiene el usuario desde el token"""
        try:
            token_obj = Token.objects.get(key=token)
            return Usuario.objects.get(user=token_obj.user)
        except:
            return None

    @database_sync_to_async
    def user_in_room(self, usuario, room_id):
        """Verifica si el usuario pertenece a la sala"""
        from .models import UsuarioSala
        return UsuarioSala.objects.filter(
            id_usuario=usuario,
            id_sala_id=room_id
        ).exists()

    @database_sync_to_async
    def save_message(self, room_id, usuario_id, contenido):
        """Guarda el mensaje en la base de datos"""
        mensaje = MensajeChat.objects.create(
            id_sala_id=room_id,
            id_usuario_id=usuario_id,
            contenido=contenido
        )
        return {
            'id_mensaje': mensaje.id_mensaje,
            'contenido': mensaje.contenido,
            'fecha_envio': mensaje.fecha_envio.isoformat(),
            'usuario': {
                'id_usuario': mensaje.id_usuario.id_usuario,
                'nombre_usuario': mensaje.id_usuario.nombre_usuario,
                'foto_perfil': mensaje.id_usuario.foto_perfil,
            }
        }

    @database_sync_to_async
    def get_recent_messages(self, room_id, limit=50):
        """Obtiene los últimos N mensajes de la sala"""
        mensajes = MensajeChat.objects.filter(
            id_sala_id=room_id,
            estado='activo'
        ).select_related('id_usuario').order_by('-fecha_envio')[:limit]

        return [{
            'id_mensaje': m.id_mensaje,
            'contenido': m.contenido,
            'fecha_envio': m.fecha_envio.isoformat(),
            'usuario': {
                'id_usuario': m.id_usuario.id_usuario,
                'nombre_usuario': m.id_usuario.nombre_usuario,
                'foto_perfil': m.id_usuario.foto_perfil,
            }
        } for m in reversed(mensajes)]
