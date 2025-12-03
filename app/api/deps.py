from __future__ import annotations

from typing import Annotated, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.config import settings
from app.core.security import decode_token
from app.db.models import User

# --- Role enum: підтримує і RoleEnum, і Role; і 'operator', і 'agent' ---
try:
    from app.db.models import RoleEnum as Role  # нова назва
except Exception:
    from app.db.models import Role              # стара назва

# alias-и на випадок різних назв у старому коді
RoleOperator = getattr(Role, "operator", getattr(Role, "agent", None))
RoleAgent    = getattr(Role, "agent", getattr(Role, "operator", None))

# Порядок прав: менше число = менше прав (динамічно будуємо словник, щоб не падати)
ROLE_ORDER: Dict[Role, int] = {}
ROLE_ORDER[getattr(Role, "user")] = 0
if RoleAgent is not None:
    ROLE_ORDER[RoleAgent] = 1
if RoleOperator is not None:
    # якщо обидва існують — вважаємо їх еквівалентними за рангом
    ROLE_ORDER[RoleOperator] = ROLE_ORDER.get(RoleAgent, 1)
ROLE_ORDER[getattr(Role, "admin")] = 2

# OAuth2 bearer (для інтеграції з /api/docs)
# Зверни увагу: у нас префікс /api в main.py, тож вкажемо повний шлях:
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Тип для DI сесії БД
DBDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    db: DBDep,
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Декодує Bearer JWT, дістає користувача з БД і перевіряє активність.
    """
    try:
        payload = decode_token(token, settings.jwt_secret)
        email: str | None = payload.get("sub")
        if not email:
            raise ValueError("no_sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    return user


def require_role(*allowed: Role):
    """
    Пускає лише користувачів, чия роль входить у перелік allowed.
    Приклад: @router.get(..., dependencies=[Depends(require_role(Role.admin))])
    """
    allowed_set = set(allowed)

    async def _guard(current: Annotated[User, Depends(get_current_user)]) -> User:
        if getattr(current, "role", None) not in allowed_set:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current

    return _guard


def require_min_role(min_role: Role):
    """
    Пускає користувачів з роллю не нижче за min_role (за ROLE_ORDER).
    Приклад: Depends(require_min_role(RoleOperator))
    """
    min_rank = ROLE_ORDER.get(min_role, 99)

    async def _guard(current: Annotated[User, Depends(get_current_user)]) -> User:
        rank = ROLE_ORDER.get(getattr(current, "role", None), -1)
        if rank < min_rank:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current

    return _guard


# Зручні шорткати (працюють і коли роль зветься agent, і коли operator)
def require_operator():
    # візьмемо будь-який з доступних «середніх» рівнів
    mid = RoleOperator if RoleOperator is not None else RoleAgent
    return require_min_role(mid if mid is not None else getattr(Role, "user"))

def require_admin():
    return require_min_role(getattr(Role, "admin"))
