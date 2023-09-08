import asyncio
from typing import Callable

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class AsynchronousScheduler:
    _instance: AsyncIOScheduler | None = None

    @classmethod
    async def add_job(cls, func: Callable, **kwargs) -> None:
        cls._instance = AsyncIOScheduler(timezone=pytz.timezone("Pacific/Auckland")) if cls._instance is None else cls._instance
        cls._instance.add_job(func, "cron", **kwargs)
        if not cls._instance.running:
            cls._instance.start()
