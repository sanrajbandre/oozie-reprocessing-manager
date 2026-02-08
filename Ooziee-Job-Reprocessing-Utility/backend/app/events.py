import json
import redis
from .settings import settings

def publish_event(payload: dict):
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.publish(settings.redis_channel, json.dumps(payload, default=str))
    except Exception:
        pass
