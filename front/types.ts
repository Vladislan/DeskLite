export type TaskStatus =
    | 'new'
    | 'triage'
    | 'in_progress'
    | 'blocked'
    | 'done'
    | 'canceled'
    | 'archived'

export interface Task {
    id: number | string
    title: string
    description?: string
    deadline?: string
    status: TaskStatus
    assignee_id?: number | string | null

    // нові поля заявки
    dept?: 'dev' | 'impl' | 'info' | 'mgmt'
    topic?: string
    position?: string
    phone?: string
    work_email?: string
    backup_email?: string
}

export interface Paginated<T> {
    page: number
    limit: number
    total: number
    items: T[]
}

/** Q&A типи щоб імпорти в компонентах не ламались */
export type QStatus = 'new' | 'answered' | 'closed'
export interface Question {
    id: number
    author_id: number
    title: string
    content: string
    status: QStatus
    created_at: string
}
export interface Answer {
    id: number
    question_id: number
    operator_id: number | null
    content: string
    created_at: string
}
