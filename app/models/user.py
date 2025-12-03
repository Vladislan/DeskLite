from sqlalchemy import Column, Integer, String, Boolean, UniqueConstraint
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    # ...
    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
    )