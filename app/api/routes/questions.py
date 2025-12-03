# app/api/routes/questions.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func

from app.api.deps import get_current_user, DBDep
from app.db.models import User, Question, Answer, QuestionStatusEnum, RoleEnum as Role
from app.schemas.questions import QuestionCreate, QuestionOut, AnswerCreate, AnswerOut

router = APIRouter(prefix="/questions", tags=["questions"])

UserDep = Depends(get_current_user)


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(body: QuestionCreate, db: DBDep, current: User = UserDep):
    q = Question(author_id=current.id, title=body.title, content=body.content)
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


@router.get("", response_model=list[QuestionOut])
async def list_questions(
    db: DBDep,
    current: User = UserDep,
    status: str | None = Query(None),
    author_id: int | None = Query(None),
    limit: int = 50,
    offset: int = 0,
):
    stmt = select(Question)

    if current.role == Role.user:
        stmt = stmt.where(Question.author_id == current.id)
    elif author_id:
        stmt = stmt.where(Question.author_id == author_id)

    if status:
        try:
            status_enum = QuestionStatusEnum(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")
        stmt = stmt.where(Question.status == status_enum)

    stmt = stmt.order_by(Question.created_at.desc()).limit(limit).offset(offset)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{qid}/answers", response_model=list[AnswerOut])
async def list_answers(qid: int, db: DBDep, current: User = UserDep):
    q = await db.get(Question, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if current.role == Role.user and q.author_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(Answer).where(Answer.question_id == qid).order_by(Answer.created_at.asc())
    return (await db.execute(stmt)).scalars().all()


@router.post("/{qid}/answer", response_model=AnswerOut)
async def answer(qid: int, body: AnswerCreate, db: DBDep, current: User = UserDep):
    if current.role not in {Role.operator, Role.admin}:
        raise HTTPException(status_code=403, detail="Only operator/admin can answer")

    q = await db.get(Question, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    a = Answer(question_id=qid, operator_id=current.id, content=body.content)
    db.add(a)

    q.status = QuestionStatusEnum.answered
    q.updated_at = func.now()

    await db.commit()
    await db.refresh(a)
    return a


@router.patch("/{qid}/close", response_model=QuestionOut)
async def close(qid: int, db: DBDep, current: User = UserDep):
    q = await db.get(Question, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if current.role != Role.admin and q.author_id != current.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    q.status = QuestionStatusEnum.closed
    q.updated_at = func.now()
    await db.commit()
    await db.refresh(q)
    return q
