import asyncio, json
from typing import Set
from fastapi import WebSocket
from redis import asyncio as aioredis
from .settings import settings

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            self.active.discard(websocket)

    async def broadcast(self, message: dict):
        data = json.dumps(message, default=str)
        async with self.lock:
            conns = list(self.active)
        for ws in conns:
            try:
                await ws.send_text(data)
            except Exception:
                await self.disconnect(ws)

manager = ConnectionManager()

class RedisBroadcaster:
    def __init__(self):
        self.redis = None
        self.task = None

    async def start(self):
        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(settings.redis_channel)

        async def _loop():
            try:
                async for msg in pubsub.listen():
                    if msg is None:
                        continue
                    if msg.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(msg.get("data"))
                        await manager.broadcast(payload)
                    except Exception:
                        continue
            finally:
                try:
                    await pubsub.unsubscribe(settings.redis_channel)
                    await pubsub.close()
                except Exception:
                    pass

        self.task = asyncio.create_task(_loop())

    async def stop(self):
        if self.task:
            self.task.cancel()
        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass

broadcaster = RedisBroadcaster()
