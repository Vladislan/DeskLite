# app/api/routes/desk.py або окремий tasks.py
from fastapi import APIRouter, Depends
from app.api.routes import tickets as t

router = APIRouter()

@router.get("/tasks")
async def list_tasks_proxy(page: int = 1, limit: int = 10, dep=Depends(t.DBDep)):
    return await t.list_tickets(page=page, limit=limit, db=dep)

@router.post("/tasks")
async def create_task_proxy(payload: t.TicketCreate, dep=Depends(t.DBDep)):
    return await t.create_ticket(payload, db=dep)

@router.patch("/tasks/{ticket_id}")
async def update_task_proxy(ticket_id: int, payload: t.TicketUpdate, dep=Depends(t.DBDep)):
    return await t.update_ticket(ticket_id, payload, db=dep)
