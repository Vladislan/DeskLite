from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.db import get_async_session
from app.models.user import User
from app.core.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
async def register(payload: dict, db: AsyncSession = Depends(get_async_session)):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = User(email=email, password_hash=hash_password(password), role="user")
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Унікальний індекс спрацював — повертаємо конфлікт
        raise HTTPException(status_code=409, detail="Користувач з таким email уже існує")
    await db.refresh(user)
    return {"id": user.id, "email": user.email}