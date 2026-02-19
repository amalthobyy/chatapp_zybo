import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):

   
    async def connect(self):
      
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.user     = self.scope['user']
        self.other_id = self.scope['url_route']['kwargs']['user_id']

       
        ids            = sorted([self.user.id, int(self.other_id)])
        self.room_name = f"chat_{ids[0]}_{ids[1]}"

      
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

       
        await self.set_online_status(True)

        
        await self.channel_layer.group_send(self.room_name, {
            'type':    'user_status',
            'user_id': self.user.id,
            'status':  'online',
        })

    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

      
        await self.set_online_status(False)

       
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_send(self.room_name, {
                'type':    'user_status',
                'user_id': self.user.id,
                'status':  'offline',
            })

 
    async def receive(self, text_data):
        data     = json.loads(text_data)
        msg_type = data.get('type', 'message')

       
        if msg_type == 'typing':
            await self.channel_layer.group_send(self.room_name, {
                'type':      'typing_indicator',
                'user_id':   self.user.id,
                'is_typing': data.get('is_typing', False),
            })
            return

      
        content = data.get('message', '').strip()

        if not content:
            return

        
        message = await self.save_message(content)

        
        await self.channel_layer.group_send(self.room_name, {
            'type':        'chat_message',
            'message_id':  message.id,
            'message':     content,
            'sender_id':   self.user.id,
            'sender_name': self.user.username,
            'timestamp':   message.timestamp.strftime('%H:%M'),
            'is_read':     False,
        })


    async def chat_message(self, event):
        """Send chat message to WebSocket client"""
        await self.send(text_data=json.dumps({
            'type':        'message',
            'message_id':  event['message_id'],
            'message':     event['message'],
            'sender_id':   event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp':   event['timestamp'],
            'is_read':     event['is_read'],
        }))

    async def typing_indicator(self, event):
        """Forward typing indicator — but NOT back to the typer"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type':      'typing',
                'user_id':   event['user_id'],
                'is_typing': event['is_typing'],
            }))

    async def user_status(self, event):
        """Send online/offline status update"""
        await self.send(text_data=json.dumps({
            'type':    'status',
            'user_id': event['user_id'],
            'status':  event['status'],
        }))



    @database_sync_to_async
    def save_message(self, content):
        from .models import Message, User
        receiver = User.objects.get(id=self.other_id)
        return Message.objects.create(
            sender=self.user,
            receiver=receiver,
            content=content
        )

    @database_sync_to_async
    def set_online_status(self, status):
        from .models import User
        User.objects.filter(id=self.user.id).update(
            is_online=status,
            last_seen=timezone.now()
        )




class OnlineStatusConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.user = self.scope['user']
        self.group_name = 'online_status'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.set_online(True)

        
        await self.channel_layer.group_send(self.group_name, {
            'type':    'status_update',
            'user_id': self.user.id,
            'status':  'online',
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.set_online(False)
            await self.channel_layer.group_send(self.group_name, {
                'type':    'status_update',
                'user_id': self.user.id,
                'status':  'offline',
            })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            'type':    'status',
            'user_id': event['user_id'],
            'status':  event['status'],
        }))

    @database_sync_to_async
    def set_online(self, status):
        from .models import User
        User.objects.filter(id=self.user.id).update(
            is_online=status,
            last_seen=timezone.now()
        )