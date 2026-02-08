import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket
from redis import asyncio as aioredis

from .settings import settings

logger = logging.getLogger(__name__)


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
        self.pubsub = None

    async def start(self):
        if self.task and not self.task.done():
            return

        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(settings.redis_channel)

        async def _loop():
            try:
                async for msg in self.pubsub.listen():
                    if msg is None:
                        continue
                    if msg.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(msg.get("data"))
                        await manager.broadcast(payload)
                    except Exception:
                        continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("redis broadcast loop crashed: %s", exc)
            finally:
                try:
                    if self.pubsub:
                        await self.pubsub.unsubscribe(settings.redis_channel)
                        await self.pubsub.close()
                except Exception:
                    pass

        self.task = asyncio.create_task(_loop())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass
        self.task = None
        self.redis = None
        self.pubsub = None

broadcaster = RedisBroadcaster()
