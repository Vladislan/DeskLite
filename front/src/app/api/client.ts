// src/app/api/client.ts
import axios from 'axios'
import type { Task, TaskStatus, Paginated } from '../../../types'

/** Базовий клієнт */
export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ?? '/api',
    timeout: 100000,
})

/** Authorization: Bearer <token> */
api.interceptors.request.use((config) => {
    const tok = localStorage.getItem('token')
    if (tok) {
        if (!config.headers) config.headers = {} as any
        const h = config.headers as any
        if (typeof h.set === 'function') h.set('Authorization', `Bearer ${tok}`)
        else h['Authorization'] = `Bearer ${tok}`
    }
    return config
})

/** 401 → логаут і редірект на /login.html */
api.interceptors.response.use(
    (r) => r,
    (err) => {
        if (err?.response?.status === 401) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            window.location.href = '/login.html'
        }
        return Promise.reject(err)
    }
)

/** ===== Tickets API (замість /tasks) ===== */

export async function listTasks(page = 1, limit = 10): Promise<Paginated<Task>> {
    const { data } = await api.get('/tickets', { params: { page, limit } })
    const items = data.items ?? data.tickets ?? data.results ?? data
    return {
        page: data.page ?? page,
        limit: data.limit ?? limit,
        total: data.total ?? (Array.isArray(items) ? items.length : 0),
        items,
    }
}

export interface TicketCreatePayload {
    title: string
    description?: string
    deadline?: string
    dept?: 'dev'|'impl'|'info'|'mgmt'
    topic?: string
    position?: string
    phone?: string
    work_email?: string
    backup_email?: string
}

export async function createTask(payload: TicketCreatePayload): Promise<Task> {
    const { data } = await api.post('/tickets', payload)
    return data
}

/** М’яке видалення: скасування */
export async function deleteTask(id: Task['id']): Promise<void> {
    await api.patch(`/tickets/${id}`, { status: 'canceled' })
}

/** Жорстке видалення (hard-delete) */
export async function hardDeleteTicket(id: number | string): Promise<void> {
    const nId = typeof id === 'string' ? Number(id) : id
    await api.delete(`/tickets/${nId}`)
}

export async function updateTaskStatus(
    id: Task['id'],
    target: TaskStatus
): Promise<Task> {
    const { data } = await api.patch(`/tickets/${id}`, { status: target })
    return data
}

/** Універсальний PATCH для квитка (наприклад, статус + assignee_id разом) */
type PatchableKeys = Extract<keyof Task, 'status' | 'assignee_id' | 'priority' | 'title' | 'description'>
export async function patchTicket(
    id: number,
    payload: Partial<Pick<Task, PatchableKeys>>
): Promise<Task> {
    const { data } = await api.patch(`/tickets/${id}`, payload)
    return data
}

/** Окремі дії для модалки оператора */
export async function approveTicket(id: number | string): Promise<Task> {
    const nId = typeof id === 'string' ? Number(id) : id
    const { data } = await api.patch(`/tickets/${nId}`, { status: 'done' })
    return data
}
export async function sendToAdmin(id: number | string): Promise<Task> {
    const nId = typeof id === 'string' ? Number(id) : id
    const { data } = await api.patch(`/tickets/${nId}`, { status: 'triage' })
    return data
}

export async function health(): Promise<'ok' | string> {
    try {
        const { data } = await api.get('/health')
        return typeof data === 'string' ? data : (data.status ?? 'ok')
    } catch {
        return 'down'
    }
}

/** ===== Admin stats ===== */
export interface AdminUserStat { email: string; tickets_created: number }
export interface AdminOperatorStat {
    email: string
    in_progress: number
    done: number
    canceled: number
    avg_resolution_minutes?: number | null  // 🔹 SLA
}
export interface AdminQAStat {
    question_id: number
    title: string
    user_email: string
    answers: number
    last_answer_at?: string | null
}
export interface AdminStats {
    users: AdminUserStat[];
    operators: AdminOperatorStat[];
    qa: AdminQAStat[];
}
export async function getAdminStats(): Promise<AdminStats> {
    const { data } = await api.get('/admin/stats')
    return data as AdminStats
}

/** ===== Users ===== */
export type UserRole = 'admin' | 'operator' | 'user'
export type User = { id: number; email: string; role: UserRole; created_at?: string; is_active?: boolean }

export async function listUsers(page = 1, limit = 100): Promise<{ page: number; limit: number; total: number; items: User[] }> {
    const { data } = await api.get('/admin/users', { params: { page, limit } })
    const items: User[] = data.items ?? data.users ?? data.results ?? data
    const normalized = Array.isArray(data) ? data as User[] : items
    return {
        page,
        limit,
        total: Array.isArray(normalized) ? normalized.length : 0,
        items: normalized,
    }
}

/** заявки конкретного користувача */
export async function listUserTickets(userId: number, limit = 100) {
    const { data } = await api.get('/tickets', { params: { author_id: userId, limit } })
    return data.items ?? data.tickets ?? data.results ?? data
}

/** 🔹 Видалення користувача (для адміна) */
export async function deleteUser(id: number): Promise<void> {
    await api.delete(`/admin/users/${id}`)
}

/** ===== Q&A ===== */
export type QStatus = 'new' | 'answered' | 'closed'
export interface Question { id:number; author_id:number; title:string; content:string; status:QStatus; created_at:string }
export interface Answer { id:number; question_id:number; operator_id:number|null; content:string; created_at:string }

export async function createQuestion(payload: {title:string; content:string}): Promise<Question> {
    const {data} = await api.post('/questions', payload); return data
}
export async function listQuestions(params?: {status?:QStatus; author_id?:number; limit?:number}): Promise<Question[]> {
    const {data} = await api.get('/questions', { params }); return data
}
export async function listAnswers(qid:number): Promise<Answer[]> {
    const {data} = await api.get(`/questions/${qid}/answers`); return data
}
export async function answerQuestion(qid:number, content:string): Promise<Answer> {
    const {data} = await api.post(`/questions/${qid}/answer`, {content}); return data
}
export async function closeQuestion(qid:number): Promise<Question> {
    const {data} = await api.patch(`/questions/${qid}/close`); return data
}
export async function operatorApproveTicket(id: number|string) {
    const nId = typeof id === 'string' ? Number(id) : id
    const { data } = await api.post(`/tickets/${nId}/operator-approve`)
    return data
}

export async function adminApproveTicket(id: number|string) {
    const nId = typeof id === 'string' ? Number(id) : id
    const { data } = await api.post(`/tickets/${nId}/admin-approve`)
    return data
}

/** ===== Operator signups (NEW) ===== */
export interface OperatorSignup { id:number; email:string; full_name?:string|null; phone?:string|null }

export async function listOperatorSignups(): Promise<OperatorSignup[]> {
    const { data } = await api.get('/admin/operator-signups')
    return data as OperatorSignup[]
}

export async function approveOperatorSignup(ticketId: number): Promise<void> {
    await api.post(`/admin/operator-signups/${ticketId}/approve`)
}

/** ===== Operator productivity (для графіка) ===== */
export interface OperatorSeriesPoint { date: string; count: number; avg_minutes?: number | null }
export interface OperatorProductivity { operator_id: number; email: string; series: OperatorSeriesPoint[] }

export async function getOperatorProductivity(days = 30): Promise<OperatorProductivity[]> {
    // даємо більше часу лише для цього запиту
    const { data } = await api.get('/admin/operator-productivity', {
        params: { days },
        timeout: 45000,                 // ⬅️ довший таймаут для важкої агрегації
    })
    return data as OperatorProductivity[]
}

/** ===== Operator feedback (фідбек адміна операторам) ===== */
export interface AdminOperatorFeedback {
    id: number
    operator_id: number
    operator_email: string
    author_id: number | null
    author_email: string | null
    message: string
    created_at: string
    is_read: boolean
}

export async function sendOperatorFeedback(operatorId: number, message: string): Promise<AdminOperatorFeedback> {
    const { data } = await api.post('/admin/operator-feedback', {
        operator_id: operatorId,
        message,
    })
    return data as AdminOperatorFeedback
}

/** Отримання рекомендацій для поточного оператора */
export async function listMyOperatorFeedback(): Promise<AdminOperatorFeedback[]> {
    // 🔹 тепер оператор читає зі свого ендпоінта, а не з /admin/...
    const { data } = await api.get('/operator/feedback')
    return data as AdminOperatorFeedback[]
}

export default api
