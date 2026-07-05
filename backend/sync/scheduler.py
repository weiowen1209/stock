from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.sync.sync_tasks import (
    provider_health_probe_task,
    sync_daily_kline_task,
    sync_realtime_quotes_task,
)


_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    return _scheduler


def configure_scheduler() -> AsyncIOScheduler:
    scheduler = get_scheduler()
    if scheduler.get_job("realtime_quotes") is None:
        scheduler.add_job(
            sync_realtime_quotes_task,
            "interval",
            minutes=30,
            id="realtime_quotes",
            replace_existing=True,
            max_instances=1,
        )
    if scheduler.get_job("daily_kline") is None:
        scheduler.add_job(
            sync_daily_kline_task,
            "cron",
            hour=15,
            minute=30,
            id="daily_kline",
            replace_existing=True,
            max_instances=1,
        )
    if scheduler.get_job("provider_probe") is None:
        scheduler.add_job(
            provider_health_probe_task,
            "interval",
            minutes=30,
            id="provider_probe",
            replace_existing=True,
            max_instances=1,
        )
    return scheduler


def start_scheduler() -> None:
    scheduler = configure_scheduler()
    if not scheduler.running:
        scheduler.start()


def shutdown_scheduler() -> None:
    global _scheduler
    scheduler = _scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    _scheduler = None
