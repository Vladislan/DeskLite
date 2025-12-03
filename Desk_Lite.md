# Desk Lite

FastAPI + SQLAlchemy(Async) + PostgreSQL + Redis(RQ) · Docker/Compose

## Quickstart (local)
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

## Docker
cp .env.example .env
docker-compose up --build

## Alembic
alembic init -t async app/db/migrations
# налаштуй env.py на AsyncEngine (target_metadata з app.db.base.Base.metadata)
