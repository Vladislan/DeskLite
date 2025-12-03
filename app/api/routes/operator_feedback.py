# app/api/routes/operator_feedback.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..deps import DBDep, get_current_user, require_role
from app.db.models import User, OperatorFeedback, RoleEnum as Role

router = APIRouter()


class OperatorFeedbackOut(BaseModel):
    """
    Вихідна модель для кабінету оператора.
    Поля відповідають інтерфейсу AdminOperatorFeedback на фронті.
    """
    id: int
    operator_id: int
    operator_email: str
    author_id: Optional[int] = None
    author_email: Optional[str] = None
    message: str
    created_at: datetime
    is_read: bool

    class Config:
        orm_mode = True


@router.get(
    "/feedback",
    response_model=List[OperatorFeedbackOut],
    dependencies=[Depends(require_role(Role.operator))],
)
async def list_my_feedback(
    db: DBDep,
    current=Depends(get_current_user),
):
    """
    Рекомендації / фідбек адміністратора для поточного оператора.

    GET /api/operator/feedback
    """
    # Переконаємося, що користувач справді оператор
    if current.role != Role.operator:
        raise HTTPException(status_code=403, detail="Only operator can view feedback")

    # тягнемо всі фідбеки для цього оператора
    rows = (
        await db.execute(
            select(OperatorFeedback)
            .where(OperatorFeedback.operator_id == current.id)
            .order_by(OperatorFeedback.created_at.desc())
        )
    ).scalars().all()

    out: list[OperatorFeedbackOut] = []

    for fb in rows:
        operator_email = current.email
        author_email: Optional[str] = None

        if fb.author_id:
            author = (
                await db.execute(
                    select(User).where(User.id == fb.author_id)
                )
            ).scalar_one_or_none()
            if author:
                author_email = author.email

        out.append(
            OperatorFeedbackOut(
                id=fb.id,
                operator_id=fb.operator_id,
                operator_email=operator_email,
                author_id=fb.author_id,
                author_email=author_email,
                message=fb.message,
                created_at=fb.created_at,
                is_read=fb.is_read,
            )
        )

    return out
