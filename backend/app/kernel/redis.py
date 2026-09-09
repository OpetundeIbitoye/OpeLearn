"""Shared async Redis connection."""
from redis.asyncio import Redis

from app.kernel.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
