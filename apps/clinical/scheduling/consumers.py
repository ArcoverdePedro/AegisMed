import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .services import CALL_PANEL_GROUP, can_view_call_panel


class CallPanelConsumer(AsyncWebsocketConsumer):
    """Só avisa que houve chamada; nenhuma senha ou dado trafega pelo socket."""

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        if not await self.user_can_view_call_panel():
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(CALL_PANEL_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(CALL_PANEL_GROUP, self.channel_name)

    async def call_panel_refresh(self, event):
        # Revalida a cada evento: permissão retirada fecha o painel aberto.
        if not await self.user_can_view_call_panel():
            await self.close(code=4403)
            return
        await self.send(text_data=json.dumps({"type": "call_panel_refresh"}))

    @database_sync_to_async
    def user_can_view_call_panel(self):
        # Usuário recarregado do banco: desativação ou permissão retirada valem na hora.
        user = get_user_model().objects.filter(pk=self.user.pk, is_active=True).first()
        return bool(user and can_view_call_panel(user))
