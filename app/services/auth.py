# app/services/auth.py
from __future__ import annotations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, hash_password, create_access_token
from app.db.models import User

# Enum alias
try:
    from app.db.models import RoleEnum as RoleType  # type: ignore
except Exception:
    from app.db.models import Role as RoleType  # type: ignore


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


def _get_pwd_field_name() -> str:
    if hasattr(User, "password_hash"):
        return "password_hash"
    if hasattr(User, "hashed_password"):
        return "hashed_password"
    raise RuntimeError("Модель User не має поля пароля (password_hash / hashed_password).")


async def authenticate(db: AsyncSession, *, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    pwd_field = _get_pwd_field_name()
    hashed = getattr(user, pwd_field, None)
    if not hashed:
        return None
    if not verify_password(password, hashed):
        return None
    return user


async def register_user(
    db: AsyncSession, *, email: str, password: str, full_name: str | None = None
) -> User:
    """Явна реєстрація юзера як role=user."""
    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError("Користувач уже існує")
    pwd_field = _get_pwd_field_name()
    user = User(
        email=email,
        **{pwd_field: hash_password(password)},
        role=getattr(RoleType, "user"),
        is_active=True if hasattr(User, "is_active") else True,
        name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_user_if_allowed(db: AsyncSession, *, email: str, password: str) -> Optional[User]:
    """Зберігаємо для сумісності, але викликаємо тільки якщо allow_self_signup=True."""
    if not settings.allow_self_signup:
        return None
    existing = await get_user_by_email(db, email)
    if existing:
        return existing
    pwd_field = _get_pwd_field_name()
    user = User(
        email=email,
        **{pwd_field: hash_password(password)},
        role=getattr(RoleType, "user"),
        is_active=True if hasattr(User, "is_active") else True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def serialize_user(user: User) -> dict:
    role_value = getattr(user.role, "value", user.role)  # Enum → str
    return {
        "id": user.id,
        "email": user.email,
        "role": str(role_value),
        "name": getattr(user, "name", None),
        "is_active": getattr(user, "is_active", None),
    }


def make_token_for_user(user: User, *, remember_me: bool = False) -> str:
    """
    Створюємо access-токен.
    Якщо remember_me=True → беремо збільшений TTL з jwt_remember_expires_min.
    """
    role_value = getattr(user.role, "value", user.role)
    minutes = (
        settings.jwt_remember_expires_min
        if remember_me
        else settings.jwt_expires_min
    )
    return create_access_token(
        subject=user.email,
        role=str(role_value),
        secret=settings.jwt_secret,
        expires_minutes=minutes,
    )
