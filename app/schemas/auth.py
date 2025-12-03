# app/schemas/auth.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, EmailStr


class LoginIn(BaseModel):
    username: EmailStr
    password: str
    # нове поле: чи хоче користувач подовжену сесію
    remember_me: bool | None = None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    position: str | None = None


class RegisterOperatorIn(BaseModel):
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    name: str | None = None
    is_active: bool | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
