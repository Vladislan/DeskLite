# app/schemas/tickets.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

# Енуми: підтримуємо як нові, так і старі імена
try:
    from app.db.models import PriorityEnum as Priority
except Exception:
    from app.db.models import Priority  # старе ім'я

try:
    from app.db.models import TicketStatusEnum as Status
except Exception:
    from app.db.models import Status  # старе ім'я


Dept = Literal['dev', 'impl', 'info', 'mgmt']  # зберігаємо як короткі коди


class TicketBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    priority: Priority = Field(default=Priority.normal)

    # нові поля з форми
    dept: Optional[Dept] = Field(default=None, description="Відділ: dev|impl|info|mgmt")
    topic: Optional[str] = Field(default=None, max_length=255)
    position: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)
    work_email: Optional[str] = Field(default=None, max_length=255)
    backup_email: Optional[str] = Field(default=None, max_length=255)


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    # усі поля опційні; змінюються частково
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    assignee_id: Optional[int] = None

    # дозволимо оновлювати теж (для оператора/адміна, або автора на ранніх стадіях)
    dept: Optional[Dept] = None
    topic: Optional[str] = Field(default=None, max_length=255)
    position: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)
    work_email: Optional[str] = Field(default=None, max_length=255)
    backup_email: Optional[str] = Field(default=None, max_length=255)


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    priority: Priority
    status: Status
    author_id: int
    assignee_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # нові поля мають бути у відповіді!
    dept: Optional[Dept] = None
    topic: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    work_email: Optional[str] = None
    backup_email: Optional[str] = None

    class Config:
        from_attributes = True
