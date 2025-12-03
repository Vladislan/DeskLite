"""
Tickets service (бізнес-правила для заявок)

Тут живе state machine і базові перевірки прав редагування.
Роутери можуть імпортувати ці функції, щоб не дублювати логіку.
"""

from typing import Set
from app.db.models import Status, Role

# Допустимі переходи (state machine)
ALLOWED_TRANSITIONS: dict[Status, Set[Status]] = {
    Status.open: {Status.in_progress, Status.done},
    Status.in_progress: {Status.waiting_for_customer, Status.on_hold, Status.done},
    Status.waiting_for_customer: {Status.in_progress, Status.done},
    Status.on_hold: {Status.in_progress},
    Status.done: {Status.in_progress},  # reopen
}

def can_transition(src: Status, dst: Status) -> bool:
    """
    Перевіряє, чи дозволено перейти зі стану src до dst.
    """
    return dst in ALLOWED_TRANSITIONS.get(src, set())

def can_user_close_their_own(status: Status) -> bool:
    """
    Автор-User може закрити свою заявку? (політика MVP — так, у будь-якому активному стані).
    За потреби звузимо до open|in_progress.
    """
    return status in {Status.open, Status.in_progress, Status.waiting_for_customer, Status.on_hold}

def can_edit_title_description(user_role: Role, is_author: bool, status: Status) -> bool:
    """
    Редагування основних полів:
      - автор може, лише коли заявка у 'open';
      - agent/admin можуть будь-коли.
    """
    return (is_author and status == Status.open) or (user_role in {Role.agent, Role.admin})

def can_assign(user_role: Role) -> bool:
    """
    Призначення/перепризначення виконавця — лише для agent/admin.
    """
    return user_role in {Role.agent, Role.admin}
