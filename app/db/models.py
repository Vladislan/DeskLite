# app/db/models.py
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ==== Енуми (python + sqlalchemy) ====


class RoleEnum(str, enum.Enum):
    user = "user"
    operator = "operator"
    admin = "admin"


class PriorityEnum(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    medium = "medium"


class TicketStatusEnum(str, enum.Enum):
    new = "new"
    triage = "triage"
    in_progress = "in_progress"  # оператор взяв у роботу
    pending_admin = "pending_admin"
    blocked = "blocked"
    done = "done"
    canceled = "canceled"
    archived = "archived"


class CommentVisibilityEnum(str, enum.Enum):
    public = "public"
    internal = "internal"


# ==== Міксини ====


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ==== Моделі ====


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="role_enum"),
        default=RoleEnum.user,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # relationships
    tickets_authored: Mapped[List["Ticket"]] = relationship(
        back_populates="author",
        foreign_keys="Ticket.author_id",
    )
    tickets_assigned: Mapped[List["Ticket"]] = relationship(
        back_populates="assignee",
        foreign_keys="Ticket.assignee_id",
    )
    comments: Mapped[List["Comment"]] = relationship(back_populates="author")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    dept: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    work_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    backup_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    priority: Mapped[PriorityEnum] = mapped_column(
        Enum(PriorityEnum, name="priority_enum"),
        default=PriorityEnum.normal,
        nullable=False,
    )
    status: Mapped[TicketStatusEnum] = mapped_column(
        Enum(TicketStatusEnum, name="ticket_status_enum"),
        default=TicketStatusEnum.new,
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # relationships
    author: Mapped["User"] = relationship(
        back_populates="tickets_authored",
        foreign_keys=[author_id],
    )
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="tickets_assigned",
        foreign_keys=[assignee_id],
    )
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tickets_status_priority", "status", "priority"),
        Index("ix_tickets_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status} priority={self.priority}>"


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    body: Mapped[str] = mapped_column(Text)
    visibility: Mapped[CommentVisibilityEnum] = mapped_column(
        Enum(CommentVisibilityEnum, name="comment_visibility_enum"),
        default=CommentVisibilityEnum.public,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    ticket: Mapped["Ticket"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64))
    ticket_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# --- Backward-compat aliases (щоб старі імпорти не падали) ---
try:
    Role  # якщо вже було старе ім'я
except NameError:
    Role = RoleEnum

try:
    Status
except NameError:
    Status = TicketStatusEnum

try:
    Priority
except NameError:
    Priority = PriorityEnum


# --- Q&A ---
from sqlalchemy import Enum as SAEnum, ForeignKey as SAForeignKey
from sqlalchemy.orm import (
    Mapped as SAMapped,
    mapped_column as sa_mapped_column,
    relationship as sa_relationship,
)


class QuestionStatusEnum(str, enum.Enum):
    new = "new"
    answered = "answered"
    closed = "closed"


class Question(Base):
    __tablename__ = "questions"

    id: SAMapped[int] = sa_mapped_column(primary_key=True)
    author_id: SAMapped[int] = sa_mapped_column(
        SAForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: SAMapped[str] = sa_mapped_column(String(255), nullable=False)
    content: SAMapped[str] = sa_mapped_column(Text, nullable=False)
    status: SAMapped[QuestionStatusEnum] = sa_mapped_column(
        SAEnum(QuestionStatusEnum, name="question_status_enum"),
        default=QuestionStatusEnum.new,
        nullable=False,
    )
    created_at: SAMapped[datetime] = sa_mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: SAMapped[datetime] = sa_mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    author: SAMapped["User"] = sa_relationship(backref="questions", lazy="joined")
    answers: SAMapped[list["Answer"]] = sa_relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"

    id: SAMapped[int] = sa_mapped_column(primary_key=True)
    question_id: SAMapped[int] = sa_mapped_column(
        SAForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operator_id: SAMapped[int] = sa_mapped_column(
        SAForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: SAMapped[str] = sa_mapped_column(Text, nullable=False)
    created_at: SAMapped[datetime] = sa_mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    question: SAMapped["Question"] = sa_relationship(back_populates="answers")
    operator: SAMapped["User"] = sa_relationship(lazy="joined")


# --- NEW: заявки на реєстрацію операторів ---


class OperatorRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OperatorSignupRequest(Base):
    __tablename__ = "operator_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[OperatorRequestStatus] = mapped_column(
        Enum(OperatorRequestStatus, name="operator_request_status_enum"),
        default=OperatorRequestStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    approved_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by],
    )


# --- NEW: Фідбек адміністратора операторам ---


class OperatorFeedback(Base):
    """
    Короткі рекомендації / фідбек від адміністратора конкретному оператору.
    Відображається в кабінеті оператора.
    """

    __tablename__ = "operator_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    operator: Mapped["User"] = relationship("User", foreign_keys=[operator_id])
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])
