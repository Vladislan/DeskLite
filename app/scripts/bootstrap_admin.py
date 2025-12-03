from __future__ import annotations

import argparse
import asyncio
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# settings
from app.core.config import settings

# моделі (і нові, і старі імена)
from app.db.models import User  # type: ignore

try:
    # новий енум
    from app.db.models import RoleEnum as RoleType  # type: ignore
except Exception:  # старий енум
    from app.db.models import Role as RoleType  # type: ignore

# спробувати використати вже сконфігуровану сесію, якщо є
try:
    from app.db.session import AsyncSessionLocal  # type: ignore
except Exception:
    AsyncSessionLocal = None  # будемо створювати нижче


# ---------- hashing ----------
def _hash_password(password: str) -> str:
    # спочатку пробуємо твій security util
    try:
        from app.core.security import hash_password as _hp  # type: ignore
        return _hp(password)
    except Exception:
        pass

    # потім passlib[bcrypt]
    try:
        from passlib.context import CryptContext  # type: ignore
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd.hash(password)
    except Exception:
        pass

    # остання спроба — чистий bcrypt
    try:
        import bcrypt  # type: ignore
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception as e:
        raise RuntimeError(
            "Не знайдено механізму хешування. Додай 'passlib[bcrypt]' або надай app.core.security.hash_password"
        ) from e


# ---------- helpers ----------
async def _get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


async def _ensure_user(
    db: AsyncSession,
    *,
    email: str,
    role: RoleType,
    password_plain: Optional[str],
    name: Optional[str],
    ensure_active: bool = True,
    update_role_if_different: bool = True,
    update_name_if_different: bool = True,
    update_activate_if_inactive: bool = True,
) -> User:
    """
    Якщо користувача немає — створює його (потрібен password_plain).
    Якщо є — оновлює роль/ім'я/активність (пароль не чіпає).
    Працює і з полем 'password_hash', і зі старим 'hashed_password'.
    """
    user = await _get_user_by_email(db, email)

    # визначимо ім'я поля для пароля та наявність is_active/name
    pwd_field = "password_hash" if hasattr(User, "password_hash") else "hashed_password" if hasattr(User, "hashed_password") else None
    has_is_active = hasattr(User, "is_active")
    has_name = hasattr(User, "name")

    if user is None:
        if not password_plain:
            raise ValueError(f"Не задано пароль для нового користувача {email}")
        if not pwd_field:
            raise RuntimeError("У моделі User відсутнє поле для пароля ('password_hash' або 'hashed_password').")

        kwargs = {
            "email": email,
            pwd_field: _hash_password(password_plain),
            "role": role,
        }
        if has_is_active:
            kwargs["is_active"] = ensure_active
        if has_name:
            kwargs["name"] = name

        user = User(**kwargs)  # type: ignore[arg-type]
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"[bootstrap] створено користувача: {email} ({role})")
        return user

    updated = False
    # роль
    if update_role_if_different and getattr(user, "role", None) != role:
        await db.execute(update(User).where(User.id == user.id).values(role=role))
        updated = True
    # ім'я
    if update_name_if_different and has_name and name and name != getattr(user, "name", None):
        await db.execute(update(User).where(User.id == user.id).values(name=name))
        updated = True
    # активність
    if update_activate_if_inactive and has_is_active and ensure_active and not getattr(user, "is_active", True):
        await db.execute(update(User).where(User.id == user.id).values(is_active=True))
        updated = True

    if updated:
        await db.commit()
        print(f"[bootstrap] оновлено користувача: {email}")
    else:
        print(f"[bootstrap] існує без змін: {email} ({getattr(user, 'role', 'unknown')})")

    return user


async def _run(
    *,
    admin_email: str,
    admin_password: str,
    admin_name: Optional[str],
    make_demo_operator: bool,
    make_demo_user: bool,
) -> None:
    # сесія
    if AsyncSessionLocal is not None:
        # використовуємо твою фабрику, якщо вона вже налаштована
        async with AsyncSessionLocal() as db:  # type: ignore[operator]
            await _seed(db, admin_email, admin_password, admin_name, make_demo_operator, make_demo_user)
    else:
        # створюємо engine самостійно
        engine = create_async_engine(settings.database_url, echo=False, future=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with session_maker() as db:
            await _seed(db, admin_email, admin_password, admin_name, make_demo_operator, make_demo_user)
        await engine.dispose()


async def _seed(
    db: AsyncSession,
    admin_email: str,
    admin_password: str,
    admin_name: Optional[str],
    make_demo_operator: bool,
    make_demo_user: bool,
) -> None:
    # 1) admin
    await _ensure_user(
        db,
        email=admin_email,
        role=getattr(RoleType, "admin"),
        password_plain=admin_password,
        name=admin_name,
        ensure_active=True,
    )

    # 2) demo operator
    if make_demo_operator:
        await _ensure_user(
            db,
            email="operator@example.com",
            role=getattr(RoleType, "operator"),
            password_plain="Operator123!",
            name="Operator",
            ensure_active=True,
        )

    # 3) demo user
    if make_demo_user:
        await _ensure_user(
            db,
            email="user@example.com",
            role=getattr(RoleType, "user"),
            password_plain="User123!",
            name="User",
            ensure_active=True,
        )

    print("[bootstrap] завершено ✅")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed admin та демо-користувачів")
    # Позиційні (необов'язкові) — для сумісності зі старою версією:
    p.add_argument("email", nargs="?", default=settings.admin_email, help="Email адміністратора")
    p.add_argument("password", nargs="?", default=settings.admin_password, help="Пароль адміністратора")

    # Додаткові параметри
    p.add_argument("-n", "--name", default=getattr(settings, "admin_name", None), help="Ім'я адміністратора")

    # Тумблери демо-користувачів
    p.add_argument("--demo-operator", dest="demo_operator", action="store_true", help="Створити demo-оператора")
    p.add_argument("--no-demo-operator", dest="demo_operator", action="store_false", help="Не створювати demo-оператора")
    p.set_defaults(demo_operator=getattr(settings, "create_demo_operator", True))

    p.add_argument("--demo-user", dest="demo_user", action="store_true", help="Створити demo-користувача")
    p.add_argument("--no-demo-user", dest="demo_user", action="store_false", help="Не створювати demo-користувача")
    p.set_defaults(demo_user=getattr(settings, "create_demo_user", True))

    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.email:
        raise SystemExit("Помилка: не задано email адміністратора (аргумент або ADMIN_EMAIL у .env)")
    if not args.password:
        raise SystemExit("Помилка: не задано пароль адміністратора (аргумент або ADMIN_PASSWORD у .env)")

    asyncio.run(
        _run(
            admin_email=args.email,
            admin_password=args.password,
            admin_name=args.name,
            make_demo_operator=args.demo_operator,
            make_demo_user=args.demo_user,
        )
    )


if __name__ == "__main__":
    main()

