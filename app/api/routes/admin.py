# app/api/routes/admin.py
from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, case, cast, literal
from sqlalchemy.dialects.postgresql import INTERVAL
from pydantic import BaseModel

from ..deps import get_current_user, DBDep, require_role
from app.core.security import hash_password
from app.db.models import User, Ticket, Question, Answer
from sqlalchemy import select
# NB: узгоджені enum-и
try:
    from app.db.models import RoleEnum as Role
except Exception:
    from app.db.models import Role  # fallback

try:
    from app.db.models import TicketStatusEnum as Status
except Exception:
    from app.db.models import Status

try:
    from app.db.models import PriorityEnum as Priority
except Exception:
    from app.db.models import Priority

# NEW: модель для фідбеку операторам
try:
    from app.db.models import OperatorFeedback  # type: ignore
except Exception:  # якщо модель ще не підключена
    OperatorFeedback = None  # type: ignore

router = APIRouter()


class SetRoleRequest(BaseModel):
    role: Role


@router.get(
    "/users",
    dependencies=[Depends(require_role(Role.admin))],
    response_model=list[dict],
)
async def list_users(db: DBDep):
    # показуємо тільки активних користувачів
    rows = (
        await db.execute(
            select(User).where(User.is_active == True)  # noqa: E712
        )
    ).scalars().all()

    # Enum → str
    def _role(v):
        return v.value if hasattr(v, "value") else str(v)

    return [
        {
            "id": u.id,
            "email": u.email,
            "role": _role(u.role),
            "is_active": u.is_active,
        }
        for u in rows
    ]


@router.patch(
    "/users/{user_id}/role",
    dependencies=[Depends(require_role(Role.admin))],
)
async def set_role(user_id: int, payload: SetRoleRequest, db: DBDep):
    u = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.role = payload.role
    await db.commit()
    return {"id": u.id, "email": u.email, "role": payload.role}


@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_role(Role.admin))],
)
async def delete_user(
    user_id: int,
    db: DBDep,
    current=Depends(get_current_user),
):
    """
    М'яке видалення користувача: ставимо is_active = False.
    Використовується кнопкою "Видалити" в адмінці.
    """
    u = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # не даємо видалити самого себе
    if u.id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не можна видалити власний акаунт",
        )

    u.is_active = False
    await db.commit()
    return {"ok": True}


@router.get(
    "/reports/latest",
    dependencies=[Depends(require_role(Role.admin))],
)
async def latest_report(db: DBDep):
    by_status = (
        await db.execute(select(Ticket.status, func.count()).group_by(Ticket.status))
    ).all()
    by_priority = (
        await db.execute(
            select(Ticket.priority, func.count()).group_by(Ticket.priority)
        )
    ).all()
    return {
        "by_status": {s.value if hasattr(s, "value") else s: c for s, c in by_status},
        "by_priority": {
            p.value if hasattr(p, "value") else p: c for p, c in by_priority
        },
    }


# ===== агрегована статистика для адмін-кабінету =====


class AdminUserStat(BaseModel):
    email: str
    tickets_created: int


class AdminOperatorStat(BaseModel):
    email: str
    in_progress: int
    done: int
    canceled: int
    avg_resolution_minutes: float | None = None  # середній TTR (хв)


class AdminQAStat(BaseModel):
    question_id: int
    title: str
    user_email: str
    answers: int
    last_answer_at: str | None = None  # ISO


class AdminStatsOut(BaseModel):
    users: list[AdminUserStat]
    operators: list[AdminOperatorStat]
    qa: list[AdminQAStat]


@router.get(
    "/stats",
    dependencies=[Depends(require_role(Role.admin))],
    response_model=AdminStatsOut,
)
async def admin_stats(db: DBDep):
    # 1) Users
    users_q = (
        select(
            User.email.label("email"),
            func.count(Ticket.id).label("tickets_created"),
        )
        .select_from(User)
        .join(Ticket, Ticket.author_id == User.id, isouter=True)
        .where(User.role == Role.user)
        .group_by(User.id)
        .order_by(User.email.asc())
    )
    users_rows = (await db.execute(users_q)).all()
    users_stats = [
        AdminUserStat(email=row.email, tickets_created=int(row.tickets_created or 0))
        for row in users_rows
    ]

    # 2) Operators + SLA
    op_q = (
        select(
            User.email.label("email"),
            func.coalesce(
                func.sum(
                    case((Ticket.status == Status.in_progress, 1), else_=0)
                ),
                0,
            ).label("in_progress"),
            func.coalesce(
                func.sum(case((Ticket.status == Status.done, 1), else_=0)),
                0,
            ).label("done"),
            func.coalesce(
                func.sum(
                    case((Ticket.status == Status.canceled, 1), else_=0)
                ),
                0,
            ).label("canceled"),
            func.avg(
                case(
                    (
                        Ticket.status == Status.done,
                        func.extract(
                            "epoch", Ticket.resolved_at - Ticket.created_at
                        )
                        / 60.0,
                    ),
                    else_=None,
                )
            ).label("avg_resolution_minutes"),
        )
        .select_from(User)
        .join(Ticket, Ticket.assignee_id == User.id, isouter=True)
        .where(User.role == Role.operator)
        .where(User.is_active == True)  # тільки активні оператори  # noqa: E712
        .group_by(User.id)
        .order_by(User.email.asc())
    )
    op_rows = (await db.execute(op_q)).all()
    operators_stats: list[AdminOperatorStat] = []
    for row in op_rows:
        avg_val = (
            float(row.avg_resolution_minutes)
            if getattr(row, "avg_resolution_minutes", None) is not None
            else None
        )
        operators_stats.append(
            AdminOperatorStat(
                email=row.email,
                in_progress=int(row.in_progress or 0),
                done=int(row.done or 0),
                canceled=int(row.canceled or 0),
                avg_resolution_minutes=avg_val,
            )
        )

    # 3) QA
    qa_q = (
        select(
            Question.id.label("question_id"),
            Question.title.label("title"),
            User.email.label("user_email"),
            func.count(Answer.id).label("answers"),
            func.max(Answer.created_at).label("last_answer_at"),
        )
        .join(User, User.id == Question.author_id)
        .join(Answer, Answer.question_id == Question.id, isouter=True)
        .group_by(Question.id, Question.title, User.email)
        .order_by(Question.created_at.desc())
        .limit(100)
    )
    qa_rows = (await db.execute(qa_q)).all()
    qa_stats = [
        AdminQAStat(
            question_id=row.question_id,
            title=row.title,
            user_email=row.user_email,
            answers=int(row.answers or 0),
            last_answer_at=(
                row.last_answer_at.isoformat() if row.last_answer_at else None
            ),
        )
        for row in qa_rows
    ]

    return AdminStatsOut(
        users=users_stats,
        operators=operators_stats,
        qa=qa_stats,
    )


# ===== заявки на операторів =====


class OperatorSignupOut(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    phone: str | None = None


@router.get(
    "/operator-signups",
    dependencies=[Depends(require_role(Role.admin))],
    response_model=list[OperatorSignupOut],
)
async def list_operator_signups(db: DBDep):
    q = (
        select(
            Ticket.id,
            Ticket.work_email.label("email"),
            Ticket.position.label("full_name"),
            Ticket.phone,
        )
        .where(Ticket.topic == "operator_signup")
        .where(Ticket.status == Status.pending_admin)
        .order_by(Ticket.created_at.desc())
    )
    rows = (await db.execute(q)).all()
    return [
        OperatorSignupOut(
            id=r.id,
            email=r.email,
            full_name=r.full_name,
            phone=r.phone,
        )
        for r in rows
    ]


@router.post(
    "/operator-signups/{ticket_id}/approve",
    dependencies=[Depends(require_role(Role.admin))],
)
async def approve_operator_signup(ticket_id: int, db: DBDep):
    # 1) знайти тікет-заявку
    t = (
        await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ).scalar_one_or_none()
    if not t or t.topic != "operator_signup":
        raise HTTPException(status_code=404, detail="Заявку не знайдено")

    # 2) e-mail з заявки
    email = (t.work_email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="У заявці відсутній email")

    # 3) знайти / створити користувача та призначити роль operator
    u = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if not u:
        u = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            role=Role.operator,
            is_active=True,
            name=t.position,  # ПІБ клали в position
        )
        db.add(u)
        await db.flush()  # отримати id без повного commit
    else:
        u.role = Role.operator
        u.is_active = True

    # 4) закриваємо заявку
    t.status = Status.done
    t.resolved_at = func.now()

    await db.commit()
    return {"ok": True, "user_id": u.id, "email": u.email, "role": "operator"}


# ===== NEW: Продуктивність операторів для графіка в адмінці =====
class OperatorSeriesPoint(BaseModel):
    date: str   # YYYY-MM-DD
    count: int


class OperatorProductivity(BaseModel):
    operator_id: int
    email: str
    series: list[OperatorSeriesPoint]


@router.get(
    "/operator-productivity",
    dependencies=[Depends(require_role(Role.admin))],
    response_model=list[OperatorProductivity],
)
async def operator_productivity(db: DBDep, days: int = 30):
    """
    Повертає по кожному активному оператору серію по днях за останні N днів:
    [{ operator_id, email, series: [{date:'YYYY-MM-DD', count:int}, ...] }, ...]
    """
    # агрегація: скільки 'done' у кожного оператора по днях
    day_trunc = func.date_trunc("day", Ticket.resolved_at).label("d")

    # інтервал останніх N днів через CAST до INTERVAL (SQLAlchemy не приймає kwargs у make_interval)
    interval_days = cast(literal(f"{int(days)} days"), INTERVAL())

    base = (
        select(
            Ticket.assignee_id.label("op_id"),
            day_trunc,
            func.count(Ticket.id).label("cnt"),
        )
        .where(Ticket.status == Status.done)
        .where(Ticket.resolved_at.isnot(None))
        .where(Ticket.resolved_at >= func.now() - interval_days)
        .group_by(Ticket.assignee_id, day_trunc)
        .order_by(day_trunc.asc())
    )
    rows = (await db.execute(base)).all()

    # map: op_id -> [(date, count)]
    by_op: dict[int, list[OperatorSeriesPoint]] = {}
    for r in rows:
        if r.op_id is None:
            continue
        d_iso = r.d.date().isoformat() if hasattr(r.d, "date") else str(r.d)
        by_op.setdefault(int(r.op_id), []).append(OperatorSeriesPoint(date=d_iso, count=int(r.cnt)))

    # підтягуємо email-и операторів
    op_ids = list(by_op.keys())
    emails: dict[int, str] = {}
    if op_ids:
        e_rows = (await db.execute(select(User.id, User.email).where(User.id.in_(op_ids)))).all()
        emails = {int(i): e for i, e in e_rows}

    out: list[OperatorProductivity] = []
    for op_id, series in by_op.items():
        out.append(OperatorProductivity(operator_id=op_id, email=emails.get(op_id, ""), series=series))
    # відсортуємо за email для стабільності
    out.sort(key=lambda x: (x.email or "").lower())
    return out


# ===== NEW: фідбек адміністратора для операторів =====

class OperatorFeedbackCreate(BaseModel):
    operator_id: int
    message: str


class OperatorFeedbackOut(BaseModel):
    id: int
    operator_id: int
    operator_email: str   # 🔹 додали
    message: str          # 🔹 замість text
    created_at: datetime

@router.post(
    "/operator-feedback",
    dependencies=[Depends(require_role(Role.admin))],
    response_model=OperatorFeedbackOut,
)
async def create_operator_feedback(
    payload: OperatorFeedbackCreate,
    db: DBDep,
):
    if OperatorFeedback is None:
        raise HTTPException(
            status_code=500,
            detail="OperatorFeedback model is not available (нема моделі / міграції)",
        )

    # знаходимо оператора
    op = (
        await db.execute(select(User).where(User.id == payload.operator_id))
    ).scalar_one_or_none()
    if not op or op.role != Role.operator:
        raise HTTPException(status_code=404, detail="Оператора не знайдено")

    msg = payload.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Текст коментаря порожній")

    fb = OperatorFeedback(  # type: ignore
        operator_id=op.id,
        message=msg,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    return OperatorFeedbackOut(
        id=fb.id,
        operator_id=fb.operator_id,
        operator_email=op.email,
        message=fb.message,
        created_at=fb.created_at,
    )

@router.get(
    "/operator-feedback",
    dependencies=[Depends(require_role(Role.admin))],
    response_model=list[OperatorFeedbackOut],
)
async def list_operator_feedback(db: DBDep):
    """
    Останні N фідбеків адмінів операторам (якщо захочеш дивитися історію в адмінці).
    """
    if OperatorFeedback is None:
        raise HTTPException(
            status_code=500,
            detail="OperatorFeedback model is not available (нема моделі / міграції)",
        )

    rows = (
        await db.execute(
            select(OperatorFeedback, User.email.label("op_email"))
            .join(User, User.id == OperatorFeedback.operator_id)
            .order_by(OperatorFeedback.created_at.desc())
            .limit(200)
        )
    ).all()

    out: list[OperatorFeedbackOut] = []
    for fb, op_email in rows:
        out.append(
            OperatorFeedbackOut(
                id=fb.id,
                operator_id=fb.operator_id,
                operator_email=op_email,
                message=fb.message,
                created_at=fb.created_at,
            )
        )
    return out

