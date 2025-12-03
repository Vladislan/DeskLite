# app/services/notifications.py
import os
import logging
from typing import Any, Mapping

import redis
from rq import Queue

try:
    # нові версії RQ
    from rq.retry import Retry  # type: ignore
except Exception:
    # старі RQ не мають rq.retry
    Retry = None  # type: ignore

log = logging.getLogger(__name__)

DEFAULT_QUEUE = os.getenv("NOTIFICATIONS_QUEUE", "notifications")
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_queue: Queue | None = None


def _get_queue() -> Queue:
    global _queue
    if _queue is None:
        _queue = Queue(DEFAULT_QUEUE, connection=redis.from_url(DEFAULT_REDIS_URL))
    return _queue

def notify_operator_approved(ticket: dict, actor: dict) -> None:
    enqueue("ticket.operator_approved", {"ticket": ticket, "actor": actor})

def notify_admin_approved(ticket: dict, actor: dict) -> None:
    enqueue("ticket.admin_approved", {"ticket": ticket, "actor": actor})

def enqueue(event_type: str, payload: Mapping[str, Any]) -> str | None:
    """
    Кладемо подію в чергу: викликаємо handle_event у воркері.
    Якщо Retry недоступний (старий RQ) — не передаємо його.
    Повертає job.id або None у разі помилки (щоб не валити HTTP-запит).
    """
    q = _get_queue()

    # Базові аргументи для enqueue
    kwargs: dict[str, Any] = {
        "job_timeout": 60,
    }
    # Додаємо retry тільки якщо клас доступний
    if Retry is not None:
        kwargs["retry"] = Retry(max=3, interval=[5, 15, 30])

    try:
        job = q.enqueue(
            "app.workers.rq_worker.handle_event",
            event_type,
            dict(payload),
            **kwargs,
        )
        return getattr(job, "id", None)
    except Exception as e:
        # Логуємо й не піднімаємо виняток — щоб UI не отримував 500
        log.exception("Failed to enqueue event '%s': %s", event_type, e)
        return None
