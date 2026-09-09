"""Idle worker infrastructure; domain jobs are added in later phases."""
from typing import Any

from arq.connections import RedisSettings

from app.conditions.loader import load_arms
from app.kernel.config import settings


async def startup(ctx: dict[str, Any]) -> None:
    ctx["arms"] = load_arms(settings.arms_config)


async def check_redis(ctx: dict[str, Any]) -> bool:
    """Verify that the worker can execute a job and reach Redis."""
    return bool(await ctx["redis"].ping())


class WorkerSettings:
    functions = [check_redis]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
