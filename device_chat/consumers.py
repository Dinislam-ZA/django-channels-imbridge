import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Device


class DeviceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.room_group_name = f'device_{self.device_id}'

        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Отправляем текущее состояние новому пользователю
        device = await self.get_or_create_device(self.device_id)
        await self.send(text_data=json.dumps({
            'image': device.image,
            'brightness': device.brightness,
            'is_on': device.is_on
        }))

    async def disconnect(self, close_code):
        # Отсоединяемся от группы
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            # Проверка валидности данных может быть добавлена здесь
            if not ('image' in data and 'brightness' in data and 'is_on' in data):
                raise ValueError("Invalid data format")

            # Обновляем состояние в базе данных
            device = await self.update_or_create_device(data)

            # Отправляем обновленные данные всем клиентам в группе
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'device_message',
                    'image': device.image,
                    'brightness': device.brightness,
                    'is_on': device.is_on
                }
            )
        except json.JSONDecodeError as e:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON data'}))
        except ValueError as e:
            await self.send(text_data=json.dumps({'error': str(e)}))
        except Exception as e:
            await self.send(text_data=json.dumps({'error': 'An unexpected error occurred'}))

    async def device_message(self, event):
        # Отправка сообщения обратно в WebSocket
        await self.send(text_data=json.dumps({
            'image': event['image'],
            'brightness': event['brightness'],
            'is_on': event['is_on']
        }))

    @database_sync_to_async
    def get_or_create_device(self, device_id):
        device, created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={
                'image': [[0] * 16 for _ in range(16)],  # Пустой рисунок 16x16
                'brightness': 100,
                'is_on': True
            }
        )
        return device

    @database_sync_to_async
    def update_or_create_device(self, data):
        device, _ = Device.objects.update_or_create(
            device_id=self.device_id,
            defaults={
                'image': data['image'],
                'brightness': data['brightness'],
                'is_on': data['is_on']
            }
        )
        return device