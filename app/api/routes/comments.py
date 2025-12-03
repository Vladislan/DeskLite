from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..deps import get_current_user, DBDep, require_role
from app.db.models import Ticket, Comment, Role, User
from app.schemas.comments import CommentCreate, CommentOut

router = APIRouter()
UserDep = Annotated[User, Depends(get_current_user)]

@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(ticket_id: int, payload: CommentCreate, db: DBDep, current: UserDep):
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current.role == Role.user and t.author_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.is_internal and current.role == Role.user:
        raise HTTPException(status_code=403, detail="Internal comments only for agent/admin")

    c = Comment(ticket_id=ticket_id, author_id=current.id, body=payload.body, is_internal=payload.is_internal)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
async def list_comments(ticket_id: int, db: DBDep, current: UserDep):
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current.role == Role.user and t.author_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    q = select(Comment).where(Comment.ticket_id == ticket_id)
    if current.role == Role.user:
        q = q.where(Comment.is_internal == False)  # noqa: E712
    rows = (await db.execute(q)).scalars().all()
    return rows
