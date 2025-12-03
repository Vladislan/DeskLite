# app/api/routes/tickets.py
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy import update, select  # (можна залишити як є, хоча select тут вдруге)
from app.services.notifications import notify_operator_approved, notify_admin_approved

from ..deps import get_current_user, DBDep
from app.db.models import Ticket, User

# Role (operator || agent)
try:
    from app.db.models import RoleEnum as Role
except Exception:
    from app.db.models import Role  # старе ім'я

RoleOperator = getattr(Role, "operator", getattr(Role, "agent", None))
RoleAgent    = getattr(Role, "agent", getattr(Role, "operator", None))

# Status
try:
    from app.db.models import TicketStatusEnum as Status
except Exception:
    from app.db.models import Status

# Priority
try:
    from app.db.models import PriorityEnum as Priority
except Exception:
    from app.db.models import Priority

from app.schemas.tickets import TicketCreate, TicketUpdate, TicketOut
from ...services.notifications import enqueue

router = APIRouter()
UserDep = Annotated[User, Depends(get_current_user)]

ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.new: {Status.triage, Status.in_progress, Status.done, Status.canceled},
    Status.triage: {Status.in_progress, Status.blocked, Status.done, Status.canceled},
    Status.in_progress: {Status.triage, Status.blocked, Status.done, Status.canceled},
    Status.blocked: {Status.in_progress, Status.canceled},
    Status.done: {Status.in_progress, Status.triage, Status.archived},
    Status.canceled: {Status.triage, Status.in_progress},
    Status.archived: set(),
}

def can_transition(src: Status, dst: Status) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, set())

def can_edit_fields(user_role: Role, is_author: bool, status_: Status) -> bool:
    """ автор може редагувати на ранніх етапах; оператор/адмін — завжди """
    is_operator = (user_role == (RoleOperator or RoleAgent))
    is_admin = (user_role == getattr(Role, "admin"))
    return ((status_ in {Status.new, Status.triage} and is_author) or is_operator or is_admin)

@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, db: DBDep, current: UserDep):
    t = Ticket(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=Status.new,
        author_id=current.id,

        # нові поля
        dept=payload.dept,
        topic=payload.topic,
        position=payload.position,
        phone=payload.phone,
        work_email=payload.work_email,
        backup_email=payload.backup_email,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    enqueue("ticket_created", {"ticket_id": t.id, "author": current.email})
    return t

@router.get("", response_model=list[TicketOut])
async def list_tickets(
    db: DBDep,
    current: UserDep,
    status_: Status | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    assignee_id: int | None = None,
    author_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
):
    q = select(Ticket)
    if current.role == getattr(Role, "user"):
        q = q.where(Ticket.author_id == current.id)
    if status_:
        q = q.where(Ticket.status == status_)
    if priority:
        q = q.where(Ticket.priority == priority)
    if assignee_id is not None:
        q = q.where(Ticket.assignee_id == assignee_id)
    if author_id is not None and current.role != getattr(Role, "user"):
        q = q.where(Ticket.author_id == author_id)

    q = q.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return rows

@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: int, db: DBDep, current: UserDep):
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current.role == getattr(Role, "user") and t.author_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return t

@router.patch("/{ticket_id}", response_model=TicketOut)
async def patch_ticket(ticket_id: int, payload: TicketUpdate, db: DBDep, current: UserDep):
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    is_author = (t.author_id == current.id)

    # --- редагування звичайних і нових полів (однакові правила) ---
    fields_changed = any([
        payload.title is not None,
        payload.description is not None,
        payload.priority is not None,
        getattr(payload, "dept", None) is not None,
        getattr(payload, "topic", None) is not None,
        getattr(payload, "position", None) is not None,
        getattr(payload, "phone", None) is not None,
        getattr(payload, "work_email", None) is not None,
        getattr(payload, "backup_email", None) is not None,
    ])
    if fields_changed:
        if not can_edit_fields(current.role, is_author, t.status):
            raise HTTPException(status_code=403, detail="Not allowed to edit fields at this stage")
        if payload.title is not None:
            t.title = payload.title
        if payload.description is not None:
            t.description = payload.description
        if payload.priority is not None:
            t.priority = payload.priority
        if getattr(payload, "dept", None) is not None:
            t.dept = payload.dept
        if getattr(payload, "topic", None) is not None:
            t.topic = payload.topic
        if getattr(payload, "position", None) is not None:
            t.position = payload.position
        if getattr(payload, "phone", None) is not None:
            t.phone = payload.phone
        if getattr(payload, "work_email", None) is not None:
            t.work_email = payload.work_email
        if getattr(payload, "backup_email", None) is not None:
            t.backup_email = payload.backup_email

    # --- призначення ---
    if payload.assignee_id is not None:
        if current.role not in {getattr(Role, "admin"), (RoleOperator or RoleAgent)}:
            raise HTTPException(status_code=403, detail="Only operator/admin can assign")
        t.assignee_id = payload.assignee_id

    # --- зміна статусу ---
    if payload.status is not None and payload.status != t.status:
        new_status = payload.status

        if current.role == getattr(Role, "user"):
            allowed_by_role = new_status in {Status.done, Status.canceled}
        else:
            allowed_by_role = True

        # спеціальне правило: заявки dept=mgmt може затвердити лише адмін
        if new_status == Status.done and getattr(t, "dept", None) == "mgmt" and current.role != getattr(Role, "admin"):
            raise HTTPException(status_code=403, detail="Only admin can approve management tickets")

        if not allowed_by_role or not can_transition(t.status, new_status):
            raise HTTPException(status_code=400, detail="Illegal status transition")

        old = t.status
        t.status = new_status

        # --- SLA: виставляємо/скидаємо resolved_at ---
        if new_status == Status.done:
            # якщо вперше закриваємо — фіксуємо час рішення
            if t.resolved_at is None:
                t.resolved_at = func.now()
        elif old == Status.done and new_status != Status.done:
            # якщо повернули з done назад — обнуляємо resolved_at
            t.resolved_at = None

        # авто-assign
        is_operator_or_admin = current.role in {getattr(Role, "admin"), (RoleOperator or RoleAgent)}
        if is_operator_or_admin and t.assignee_id is None and payload.assignee_id is None:
            if t.status in {Status.in_progress, Status.done, Status.canceled, Status.blocked}:
                t.assignee_id = current.id

        enqueue("status_changed", {
            "ticket_id": t.id,
            "from": getattr(old, "value", str(old)),
            "to": getattr(t.status, "value", str(t.status)),
        })

    t.updated_at = func.now()
    await db.commit()
    await db.refresh(t)
    return t

# === HARD DELETE (admin/operator завжди; user — тільки свою і лише new/canceled) ===
@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(ticket_id: int, db: DBDep, current: UserDep):
    t = await db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    role = getattr(current, "role", None)
    me_id = getattr(current, "id", None)

    if role == getattr(Role, "admin"):
        pass
    elif role in {(RoleOperator or RoleAgent)}:
        pass
    else:
        if t.author_id != me_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if str(t.status) not in ("new", "canceled"):
            raise HTTPException(status_code=409, detail="Only 'new' or 'canceled' tickets can be deleted by author")

    await db.delete(t)
    await db.commit()
    return Response(status_code=204)

def _actor_payload(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "role": getattr(u.role, "value", str(u.role)),
    }

def _ticket_payload(t: Ticket, author_email: str | None = None) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "status": getattr(t.status, "value", str(t.status)),
        "priority": getattr(t.priority, "value", str(t.priority)),
        "author_id": t.author_id,
        "author_email": author_email,
        "assignee_id": t.assignee_id,
        "dept": getattr(t, "dept", None),
        "topic": getattr(t, "topic", None),
        "position": getattr(t, "position", None),
        "phone": getattr(t, "phone", None),
        "work_email": getattr(t, "work_email", None),
        "backup_email": getattr(t, "backup_email", None),
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


# --- OPERATOR APPROVE ---------------------------------------------------------

@router.post("/{ticket_id}/operator-approve")
async def operator_approve(ticket_id: int, db: DBDep, current: UserDep):
    """Погодження оператором:
       - тільки operator або admin
       - якщо статус сирий (new|triage) → ставимо in_progress
       - якщо виконавець не призначений → ставимо поточного користувача
       - шлемо подію 'operator_approved'
    """
    role = getattr(current, "role", None)
    is_operator = role in {getattr(Role, "operator", None), getattr(Role, "agent", None)}
    is_admin = role == getattr(Role, "admin", None)
    if not (is_operator or is_admin):
        raise HTTPException(status_code=403, detail="Only operator/admin can approve")

    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # e-mail автора для нотифікації
    author_email = (await db.execute(select(User.email).where(User.id == t.author_id))).scalar_one_or_none()

    # м’яке оновлення статусу: якщо заявка ще не в роботі — переведемо в in_progress
    if t.status in {Status.new, Status.triage}:
        t.status = Status.in_progress

    # авто-призначення
    if t.assignee_id is None:
        t.assignee_id = current.id

    await db.commit()
    await db.refresh(t)

    enqueue("operator_approved", {
        "ticket": _ticket_payload(t, author_email),
        "actor": _actor_payload(current),
    })

    return {"ok": True, "ticket": _ticket_payload(t, author_email)}


# --- ADMIN APPROVE ------------------------------------------------------------

@router.post("/{ticket_id}/admin-approve")
async def admin_approve(ticket_id: int, db: DBDep, current: UserDep):
    """Погодження адміністратором (фінальне):
       - тільки admin
       - статус → done
       - якщо виконавець не призначений → ставимо поточного користувача
       - шлемо подію 'admin_approved'
    """
    if getattr(current, "role", None) != getattr(Role, "admin", None):
        raise HTTPException(status_code=403, detail="Only admin can approve")

    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    author_email = (await db.execute(select(User.email).where(User.id == t.author_id))).scalar_one_or_none()

    # фіналізація
    t.status = Status.done
    if t.assignee_id is None:
        t.assignee_id = current.id
    # SLA: фіксуємо час рішення, якщо ще не був
    if t.resolved_at is None:
        t.resolved_at = func.now()

    await db.commit()
    await db.refresh(t)

    enqueue("admin_approved", {
        "ticket": _ticket_payload(t, author_email),
        "actor": _actor_payload(current),
    })

    return {"ok": True, "ticket": _ticket_payload(t, author_email)}
