"""
Reports service (MVP)

Повертає агреговані зрізи по заявках. Без збереження у таблицю snapshot.
(За потреби додамо модель ReportSnapshot і persisted snapshots).
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Ticket, Status, Priority

def _enum_key(v):
    # Повертаємо string-значення навіть якщо SQLAlchemy віддасть Enum-об'єкт
    return v.value if hasattr(v, "value") else v

async def latest_report(db: AsyncSession) -> Dict[str, Any]:
    """
    Формуємо простий звіт:
      - розподіл за статусом
      - розподіл за пріоритетом
      - скільки закрито за останні 24 години
    """
    by_status_rows = (await db.execute(
        select(Ticket.status, func.count()).group_by(Ticket.status)
    )).all()
    by_priority_rows = (await db.execute(
        select(Ticket.priority, func.count()).group_by(Ticket.priority)
    )).all()

    # closed last 24h (created_at/updated_at за потреби можна деталізувати)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    closed_24h = (await db.execute(
        select(func.count()).where(
            Ticket.status == Status.done,
            Ticket.updated_at >= since.replace(tzinfo=None),  # наші поля naive UTC
        )
    )).scalar_one()

    return {
        "by_status": { _enum_key(s): c for s, c in by_status_rows },
        "by_priority": { _enum_key(p): c for p, c in by_priority_rows },
        "closed_last_24h": int(closed_24h),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
