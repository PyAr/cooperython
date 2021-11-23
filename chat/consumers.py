import sys
import json
import asyncio
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from io import StringIO 



class ChatConsumer(AsyncWebsocketConsumer):

    refs_globals = {}
    refs_locals = {}

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

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
                'message': dict(msg=message, type_of='input')
            }
        )

        try:
            with Capturing() as output:
                try:
                    out = eval(message, self.refs_globals, self.refs_locals)
                except Exception as foo:
                    out = exec(message, self.refs_globals, self.refs_locals)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': dict(msg="\n".join(output), type_of='output')
                }
            )

        except Exception as e:

            error = traceback.format_exception(type(e), e, e.__traceback__)
            msg_error = "\n".join(error) + "\n" + str(e)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': dict(msg=msg_error, type_of='exception')
                }
            )
        else:
            if out is not None:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': dict(msg=out, type_of='output')
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        serialized_msg = json.dumps({
            'message': message['msg'],
            'typeof': message['type_of']
        })
        await self.send(text_data=serialized_msg)



class Capturing(list):

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout
