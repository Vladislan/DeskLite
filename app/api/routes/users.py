# app/api/routes/users.py
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.deps import get_current_user, require_admin, require_operator
from app.services.auth import serialize_user, hash_password
from app.schemas.users import UserOut, UsersPage, UserUpdateSelf, UserAdminUpdate
from app.db.models import User

# підтримка старих/нових назв ролей
try:
    from app.db.models import RoleEnum as Role
except Exception:
    from app.db.models import Role  # type: ignore

router = APIRouter()
DBDep = Depends(get_session)

# ---------- SELF ----------
@router.get("/me", response_model=UserOut)
async def get_me(current = Depends(get_current_user)):
    return UserOut(**serialize_user(current))

@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdateSelf, db: AsyncSession = DBDep, current = Depends(get_current_user)):
    changed = False

    if payload.name is not None:
        current.name = payload.name
        changed = True

    if payload.password:
        # визначимо реальне поле пароля
        pwd_field = "password_hash" if hasattr(User, "password_hash") else "hashed_password"
        setattr(current, pwd_field, hash_password(payload.password))
        changed = True

    if not changed:
        return UserOut(**serialize_user(current))

    current.updated_at = func.now()
    await db.commit()
    await db.refresh(current)
    return UserOut(**serialize_user(current))

# ---------- OPERATOR / ADMIN ----------
@router.get("", response_model=UsersPage, dependencies=[Depends(require_operator())])
async def list_users(
    db: AsyncSession = DBDep,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="search by email/name"),
    role: Optional[str] = Query(None, description="user|operator|admin"),
    is_active: Optional[bool] = Query(None),
):
    stmt = select(User)
    if q:
        # простий фільтр (ILIKE по email/name). Для asyncpg + SQLAlchemy — можна використати lower() порівняння
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like) | func.lower(User.name).like(like))
    if role:
        # зіставимо рядок із Enum або plain str
        # якщо модель має Enum — переведемо через getattr(Role, role)
        try:
            role_val = getattr(Role, role)
        except Exception:
            role_val = role  # fallback — якщо у полі збережено plain string
        stmt = stmt.where(User.role == role_val)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    total = (await db.execute(stmt.with_only_columns(func.count()))).scalar_one()
    rows = (await db.execute(stmt.order_by(User.id.asc()).limit(limit).offset((page - 1) * limit))).scalars().all()

    return UsersPage(
        items=[UserOut(**serialize_user(u)) for u in rows],
        total=int(total or 0),
        page=page,
        limit=limit,
    )

@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_operator())])
async def get_user(user_id: int, db: AsyncSession = DBDep):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**serialize_user(u))

@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin())])
async def admin_update_user(user_id: int, payload: UserAdminUpdate, db: AsyncSession = DBDep):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    changed = False

    if payload.name is not None:
        u.name = payload.name
        changed = True

    if payload.is_active is not None:
        u.is_active = payload.is_active
        changed = True

    if payload.role is not None:
        # конвертуємо рядок у Enum, якщо треба
        try:
            new_role = getattr(Role, payload.role)
        except Exception:
            new_role = payload.role
        u.role = new_role
        changed = True

    if not changed:
        return UserOut(**serialize_user(u))

    u.updated_at = func.now()
    await db.commit()
    await db.refresh(u)
    return UserOut(**serialize_user(u))
