import asyncio
from typing import Callable, Dict, Any

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class AsynchronousScheduler:
    _instance: AsyncIOScheduler | None = None

    @classmethod
    async def add_job(cls, func: Callable, **kwargs: Dict[str, Any]) -> None:
        """"Parameter reference: https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html#module-apscheduler.triggers.cron"""
        cls._instance = AsyncIOScheduler(timezone=pytz.timezone("Pacific/Auckland")) if cls._instance is None else cls._instance
        cls._instance.add_job(func, "cron", **kwargs)
        if not cls._instance.running:
            cls._instance.start()
