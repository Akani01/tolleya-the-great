import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AutomationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.application_id = self.scope["url_route"]["kwargs"]["application_id"]
        self.group_name = f"automation_{self.application_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def automation_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))
