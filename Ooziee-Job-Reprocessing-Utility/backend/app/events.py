import json
import logging

import redis

from .settings import settings

logger = logging.getLogger(__name__)
_redis_client = None


def _client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def publish_event(payload: dict):
    global _redis_client
    try:
        _client().publish(settings.redis_channel, json.dumps(payload, default=str))
    except Exception as exc:
        logger.warning("failed to publish event: %s", exc.__class__.__name__)
        _redis_client = None
