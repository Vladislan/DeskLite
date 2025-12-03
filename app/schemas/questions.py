from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

QuestionStatus = Literal["new","answered","closed"]

class QuestionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=2)

class QuestionOut(BaseModel):
    id: int
    author_id: int
    title: str
    content: str
    status: QuestionStatus
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class AnswerCreate(BaseModel):
    content: str = Field(min_length=1)

class AnswerOut(BaseModel):
    id: int
    question_id: int
    operator_id: int | None
    content: str
    created_at: datetime
    class Config: from_attributes = True
