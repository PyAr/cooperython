import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
import traceback

class ChatConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.refs_globals = {}
        self.refs_locals = {}

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

        try:
            try:
                out = eval(message, self.refs_globals, self.refs_locals)
            except Exception as foo:
                out = exec(message, self.refs_globals, self.refs_locals)
        except Exception as e:

            error = traceback.format_exception(type(e), e, e.__traceback__)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': "\n".join(error) + "\n" + str(e)
                }
            )
        else:
            if out != None:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': out
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

