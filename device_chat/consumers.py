import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Device


class DeviceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.room_group_name = f'device_{self.device_id}'

        try:
            device = await self.get_device(self.device_id)
        except:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Device is not exist'
            }))
            await self.close()
            return

        # Проверяем, что устройство подключено
        if not device.is_connected:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Device is not connected'
            }))
            await self.close()
            return

        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Отправляем текущее состояние новому пользователю
        devices = await self.get_all_devices()
        await self.send(text_data=json.dumps({
            'type': 'device_state',
            'name': device.name,
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
            if not ('name' in data and 'image' in data and 'brightness' in data and 'is_on' in data):
                raise ValueError("Invalid data format")

            # Обновляем состояние в базе данных
            device = await self.update_or_create_device(data)

            # Отправляем обновленные данные всем клиентам в группе
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'device_message',
                    'name': device.name,
                    'image': device.image,
                    'brightness': device.brightness,
                    'is_on': device.is_on
                }
            )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Invalid JSON data'}))
        except ValueError as e:
            await self.send(text_data=json.dumps({'type': 'error', 'message': str(e)}))
        except Exception:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'An unexpected error occurred'}))

    async def device_message(self, event):
        # Отправка сообщения обратно в WebSocket
        await self.send(text_data=json.dumps({
            'type': 'device_message',
            'name': event['name'],
            'image': event['image'],
            'brightness': event['brightness'],
            'is_on': event['is_on']
        }))

    @database_sync_to_async
    def is_device_connected(self, device_id):
        try:
            device = Device.objects.get(device_id=device_id)
            return device.is_connected
        except Device.DoesNotExist:
            return False

    @database_sync_to_async
    def get_device(self, device_id):
        device = Device.objects.get(device_id = device_id)
        return device

    @database_sync_to_async
    def update_or_create_device(self, data):
        device, _ = Device.objects.update_or_create(
            device_id=self.device_id,
            defaults={
                'name': data['name'],
                'image': data['image'],
                'brightness': data['brightness'],
                'is_on': data['is_on']
            }
        )
        return device

    @database_sync_to_async
    def get_all_devices(self):
        devices = Device.objects.all()
        return [{'device_id': device.device_id, 'name': device.name, 'is_connected': device.is_connected} for device in
                devices]


class DeviceStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.room_group_name = f'device_{self.device_id}'

        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        device = await self.get_or_create_device(self.device_id)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'device_state',
            'name': device.name,
            'image': device.image,
            'brightness': device.brightness,
            'is_on': device.is_on
        }))

        # Обновляем статус подключения устройства
        await self.update_device_status(True)

    async def disconnect(self, close_code):
        # Отсоединяемся от группы
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Обновляем статус подключения устройства
        await self.update_device_status(False)

    async def device_message(self, event):
        # Обработка сообщения от другого консьюмера
        await self.send(text_data=json.dumps({
            'type': 'device_message',
            'name': event['name'],
            'image': event['image'],
            'brightness': event['brightness'],
            'is_on': event['is_on']
        }))

    @database_sync_to_async
    def get_or_create_device(self, device_id):
        device, created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={
                'name': f'device-{device_id}',
                'image': [[0] * 16 for _ in range(16)],  # Пустой рисунок 16x16
                'brightness': 100,
                'is_on': True
            }
        )
        return device

    @database_sync_to_async
    def update_device_status(self, is_connected):
        Device.objects.filter(device_id=self.device_id).update(is_connected=is_connected)
