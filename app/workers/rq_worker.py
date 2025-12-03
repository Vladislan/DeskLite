# app/workers/rq_worker.py
import os
import logging
import json
import hmac, hashlib
from typing import Any, Mapping

import redis
import requests
from rq import Queue, Worker

from app.core.config import settings
from app.core.logging import setup_logging

QUEUE_NAME = os.getenv("NOTIFICATIONS_QUEUE", "notifications")
logger = logging.getLogger("worker.notifications")

def _sign(payload: Mapping[str, Any]) -> str | None:
    if not settings.webhook_secret:
        return None
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hmac.new(settings.webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

def _post(url: str, event_type: str, payload: Mapping[str, Any]) -> None:
    if not url:
        logger.warning("webhook_url_missing", extra={"event_type": event_type})
        return
    headers = {"Content-Type": "application/json", "X-DeskLite-Event": event_type}
    sig = _sign(payload)
    if sig:
        headers["X-DeskLite-Signature"] = f"sha256={sig}"
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    logger.info("webhook_sent", extra={"event_type": event_type, "status": r.status_code})

def send_mail_mock(to: str, subject: str, body: str) -> None:
    logger.info("SEND_MAIL", extra={"to": to, "subject": subject, "body_len": len(body)})

def on_ticket_created(payload: Mapping[str, Any]) -> None:
    ticket_id = payload.get("ticket_id")
    author = payload.get("author")
    logger.info("ticket_created", extra={"ticket_id": ticket_id, "author": author})
    if author:
        send_mail_mock(author, f"Ticket #{ticket_id} created", "Your request was registered.")

def on_status_changed(payload: Mapping[str, Any]) -> None:
    ticket_id = payload.get("ticket_id")
    old = payload.get("from")
    new = payload.get("to")
    logger.info("status_changed", extra={"ticket_id": ticket_id, "from": old, "to": new})

def on_operator_approved(payload: Mapping[str, Any]) -> None:
    _post(settings.webhook_operator_approved or "", "ticket.operator_approved", payload)
    email = payload.get("ticket", {}).get("author_email")
    tid   = payload.get("ticket", {}).get("id")
    if email:
        send_mail_mock(email, f"Заявку #{tid} погодив оператор", "Вашу заявку погоджено оператором.")

def on_admin_approved(payload: Mapping[str, Any]) -> None:
    _post(settings.webhook_admin_approved or "", "ticket.admin_approved", payload)
    email = payload.get("ticket", {}).get("author_email")
    tid   = payload.get("ticket", {}).get("id")
    if email:
        send_mail_mock(email, f"Заявку #{tid} погодив адміністратор", "Вашу заявку остаточно погоджено адміном.")

EVENT_HANDLERS: dict[str, callable] = {
    "ticket_created": on_ticket_created,
    "status_changed": on_status_changed,
    "ticket.operator_approved": on_operator_approved,
    "ticket.admin_approved": on_admin_approved,
}

def handle_event(event_type: str, payload: Mapping[str, Any] | None = None) -> None:
    handler = EVENT_HANDLERS.get(event_type)
    if not handler:
        logger.warning("unknown_event", extra={"event_type": event_type})
        return
    handler(payload or {})

def main() -> None:
    setup_logging(settings.log_level)
    logger.info("worker_starting", extra={"queue": QUEUE_NAME, "redis": settings.redis_url})
    conn = redis.from_url(settings.redis_url)
    queue = Queue(QUEUE_NAME, connection=conn)
    worker = Worker([queue], connection=conn, name=os.getenv("WORKER_NAME", "notifications-worker"))
    worker.work(logging_level=logging.INFO)

if __name__ == "__main__":
    main()
