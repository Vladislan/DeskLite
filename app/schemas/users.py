# app/schemas/users.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict

# reuse існуючий UserOut з auth? Можемо окремо дублювати, щоб не плодити залежність
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    name: str | None = None
    is_active: bool | None = None

class UserUpdateSelf(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=6, max_length=128)

class UserAdminUpdate(BaseModel):
    # допускаємо оновлення ролі та активності, а також імені
    role: str | None = None  # 'user' | 'operator' | 'admin'
    is_active: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)

class UsersPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    limit: int
