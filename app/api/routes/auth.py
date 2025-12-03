# app/api/routes/auth.py
from __future__ import annotations

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import LoginIn, TokenOut, UserOut
from app.services.auth import (
    # authenticate,  # більше не використовуємо тут, зробимо явну перевірку
    # create_user_if_allowed,  # вимикаємо авто-реєстрацію
    serialize_user,
    make_token_for_user,
)
from app.core.security import hash_password, verify_password
from app.api.deps import get_current_user

from app.db.models import User, Ticket
try:
    from app.db.models import RoleEnum as Role
except Exception:
    from app.db.models import Role as Role  # type: ignore
try:
    from app.db.models import TicketStatusEnum as Status
except Exception:
    from app.db.models import Status  # type: ignore
try:
    from app.db.models import PriorityEnum as Priority
except Exception:
    from app.db.models import Priority  # type: ignore

router = APIRouter()
DBDep = Depends(get_session)


# ===== helpers (без змін) =====

async def _get_any_admin(db: AsyncSession) -> User | None:
    res = await db.execute(
        select(User).where(User.role == Role.admin).order_by(User.id.asc()).limit(1)
    )
    return res.scalar_one_or_none()


async def _get_or_create_system_admin(db: AsyncSession) -> User:
    sys_email = "system@desklite.local"
    res = await db.execute(select(User).where(User.email == sys_email))
    u = res.scalar_one_or_none()
    if u:
        return u
    u = User(
        email=sys_email,
        password_hash=hash_password(secrets.token_urlsafe(16)),
        role=Role.admin,
        is_active=True,
        name="System",
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


# ===== login / me =====

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = DBDep):
    email = payload.username.strip().lower()
    password = payload.password or ""
    remember_me = bool(getattr(payload, "remember_me", False))

    # 1) пошук користувача
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user:
        # вимога: блокувати вхід незареєстрованих
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Данний email не є зареєстрованим",
        )

    # 2) активність (опційно)
    if hasattr(user, "is_active") and user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Акаунт не активний",
        )

    # 3) пароль
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний пароль",
        )

    # 4) токен з урахуванням remember_me
    token = make_token_for_user(user, remember_me=remember_me)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut(**serialize_user(user)),
    }


@router.get("/me", response_model=UserOut)
async def me(current=Depends(get_current_user)):
    return UserOut(**serialize_user(current))


# ===== register (звичайний користувач) =====

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    phone: str | None = None
    full_name: str | None = None
    position: str | None = None


@router.post("/register", response_model=TokenOut, status_code=201)
async def register_user(payload: RegisterIn, db: AsyncSession = DBDep):
    email = payload.email.strip().lower()

    # дублікати → 409 Conflict
    exists = await db.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач із такою поштою вже існує",
        )

    u = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=Role.user,
        is_active=True,
        name=payload.full_name,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)

    tok = make_token_for_user(u)
    return TokenOut(access_token=tok, user=UserOut(**serialize_user(u)))


# ===== register-operator (створює службовий тікет) =====

class RegisterOperatorIn(BaseModel):
    email: EmailStr
    phone: str
    full_name: str
    password: str | None = None


@router.post("/register-operator", status_code=201)
async def register_operator(payload: RegisterOperatorIn, db: AsyncSession = DBDep):
    author = await _get_any_admin(db) or await _get_or_create_system_admin(db)

    t = Ticket(
        author_id=author.id,
        title=f"Запит на реєстрацію оператора: {payload.email}",
        description=f"full_name={payload.full_name}, phone={payload.phone}",
        category="mgmt",
        priority=Priority.high,
        status=Status.pending_admin,
        topic="operator_signup",
        work_email=str(payload.email),
        phone=payload.phone,
        position=payload.full_name,
    )
    db.add(t)
    await db.commit()
    return {"ok": True, "message": "Заявку надіслано адміністратору."}


# ===== password recovery (заявки + заглушка посилань) =====

class PasswordRecoveryRequestIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    password: str


class PasswordRecoveryRequestOut(BaseModel):
    id: int
    email: EmailStr
    status: str


class SendRecoveryLinkOut(BaseModel):
    reset_url: str


@router.post("/password/recovery")
@router.post("/password-recovery-request")
async def password_recovery_request(
    payload: PasswordRecoveryRequestIn, db: AsyncSession = DBDep
):
    """
    Користувач залишає email на сторінці відновлення паролю.
    Створюємо службовий тікет topic='password_recovery'.
    """
    email = payload.email.strip().lower()

    # 🔍 перевіряємо, що користувач існує
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user:
        # тепер НЕ створюємо тікет, а повертаємо 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Користувача з таким email не знайдено",
        )

    author = await _get_any_admin(db) or await _get_or_create_system_admin(db)

    t = Ticket(
        author_id=author.id,
        title=f"Запит на відновлення паролю: {email}",
        description=f"user_id={user.id}, email={email}",
        category="mgmt",
        priority=Priority.medium,
        status=Status.pending_admin,
        topic="password_recovery",
        work_email=email,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)

    return {"ok": True}


@router.get("/password-recovery-requests", response_model=list[PasswordRecoveryRequestOut])
async def list_password_recovery_requests(
    current=Depends(get_current_user), db: AsyncSession = DBDep
):
    """
    Список заявок на відновлення паролю для адмін-панелі.
    """
    if current.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки для адмінів",
        )

    res = await db.execute(
        select(Ticket)
        .where(Ticket.topic == "password_recovery")
        .order_by(Ticket.id.desc())
    )
    tickets = res.scalars().all()

    items: list[PasswordRecoveryRequestOut] = []
    for t in tickets:
        email = t.work_email or (
            t.title.split(":", 1)[-1].strip() if ":" in t.title else ""
        )
        items.append(
            PasswordRecoveryRequestOut(
                id=t.id,
                email=email or "unknown",
                status=str(getattr(t.status, "value", t.status)),
            )
        )
    return items


@router.post(
    "/password-recovery-requests/{ticket_id}/send-link",
    response_model=SendRecoveryLinkOut,
)
async def send_recovery_link(
    ticket_id: int, current=Depends(get_current_user), db: AsyncSession = DBDep
):
    """
    Заглушка: "надіслати" посилання на відновлення.
    Насправді просто повертаємо URL для createNewPassword.html
    і позначаємо заявку як оброблену.
    """
    if current.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки для адмінів",
        )

    res = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.topic == "password_recovery",
        )
    )
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тікет не знайдено",
        )

    email = t.work_email or (
        t.title.split(":", 1)[-1].strip() if ":" in t.title else ""
    )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для тікета не вказано email",
        )

    # простий фронтенд-URL як заглушка (можеш винести в конфіг)
    frontend_url = "http://localhost:5173"
    reset_url = f"{frontend_url.rstrip('/')}/createNewPassword.html?email={email}"

    # 🔹 Позначаємо заявку як оброблену
    if hasattr(Status, "done"):
        t.status = Status.done
    elif hasattr(Status, "in_progress"):
        # fallback, якщо раптом enum без done
        t.status = Status.in_progress

    if hasattr(t, "resolved_at"):
        t.resolved_at = func.now()

    db.add(t)
    await db.commit()
    await db.refresh(t)

    return SendRecoveryLinkOut(reset_url=reset_url)


@router.post("/reset-password")
async def reset_password_api(payload: ResetPasswordIn, db: AsyncSession = DBDep):
    """
    Встановлення нового паролю (форма createNewPassword.html)
    """
    email = payload.email.strip().lower()
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Данний email не є зареєстрованим",
        )

    user.password_hash = hash_password(payload.password)
    db.add(user)
    await db.commit()

    return {"ok": True}


# ===== префлайт перевірка існування email (для UI) =====

@router.get("/check_email")
async def check_email(email: EmailStr, db: AsyncSession = DBDep):
    res = await db.execute(select(User.id).where(User.email == email.strip().lower()))
    return {"exists": res.scalar_one_or_none() is not None}
