# app/core/config.py
from typing import List, Union, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # ==== Інфраструктура ====
    database_url: str = "postgresql+asyncpg://app:app@db:5432/helpdesk"
    redis_url: str = "redis://redis:6379/0"

    # ==== Безпека / Auth ====
    jwt_secret: str = "changeme"
    jwt_alg: str = "HS256"

    # базовий час життя токена (звичайний логін), хвилини
    jwt_expires_min: int = 60  # 1 година

    # розширена сесія для "Запам’ятати мене", хвилини
    # за замовчуванням ~30 днів
    jwt_remember_expires_min: int = 60 * 24 * 30

    # ==== CORS ====
    # CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,...
    cors_origins: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5179",
        "http://127.0.0.1:5179",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # ==== Політика реєстрації ====
    allow_self_signup: bool = True

    # ==== Bootstrap Admin / Demo Users ====
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    admin_name: str = "Admin"
    create_demo_operator: bool = True
    create_demo_user: bool = True

    # ==== UI build (опційно перевизначити директорію зі SPA) ====
    ui_dist_dir: Optional[str] = None

    # ==== Логування / Оточення ====
    env: str = "dev"          # dev|staging|prod
    log_level: str = "INFO"   # DEBUG|INFO|WARNING|ERROR

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    import json
                    parsed = json.loads(s)
                    return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in s.split(",") if i.strip()]
        return v


settings = Settings()
