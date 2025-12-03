import { useEffect, useState } from 'react'
import type { Task, TaskStatus } from '../../types'
import { listTasks, deleteTask, updateTaskStatus } from '../app/api/client'

export default function TaskList() {
    const [items, setItems] = useState<Task[]>([])
    const [page, setPage] = useState(1)
    const [limit] = useState(10)
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [workingId, setWorkingId] = useState<Task['id'] | null>(null)
    const [error, setError] = useState<string | null>(null)

    const fetchPage = async (p = page) => {
        setLoading(true)
        setError(null)
        try {
            const res = await listTasks(p, limit)
            setItems(res.items)
            setTotal(res.total)
            setPage(res.page)
        } catch (err: any) {
            setError('Не вдалося отримати список задач')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { fetchPage(1) }, [])

    const changeStatus = async (id: Task['id'], target: TaskStatus) => {
        setWorkingId(id)
        setError(null)
        try {
            await updateTaskStatus(id, target)
            await fetchPage(page)
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Не вдалося змінити статус')
        } finally {
            setWorkingId(null)
        }
    }

    const remove = async (id: Task['id']) => {
        setWorkingId(id)
        setError(null)
        try {
            await deleteTask(id)
            const newPage = items.length === 1 && page > 1 ? page - 1 : page
            await fetchPage(newPage)
        } catch (err: any) {
            setError('Не вдалося видалити задачу')
        } finally {
            setWorkingId(null)
        }
    }

    const totalPages = Math.max(1, Math.ceil(total / limit))

    return (
        <div className="card">
            <h2>Задачі</h2>

            {error && <div className="muted small" style={{color:'#fca5a5', marginBottom:8}}>{error}</div>}
            {loading ? <p>Завантаження…</p> : (
                <>
                    {items.length === 0 ? (
                        <p className="muted">Список порожній</p>
                    ) : (
                        <ul className="tasks">
                            {items.map(t => {
                                const busy = workingId === t.id
                                return (
                                    <li key={t.id} className={`task task--${t.status}`}>
                                        <div className="task__main">
                                            <strong>{t.title}</strong>
                                            {t.description && <p className="muted">{t.description}</p>}
                                            <div className="muted small">
                                                Статус: <b>{t.status}</b>{t.deadline ? ` · Дедлайн: ${t.deadline}` : ''}
                                            </div>
                                        </div>
                                        <div className="task__actions">
                                            {t.status !== 'in_progress' && (
                                                <button disabled={busy} onClick={() => changeStatus(t.id, 'in_progress')}>
                                                    {busy ? '…' : 'Start'}
                                                </button>
                                            )}
                                            {t.status !== 'done' && (
                                                <button disabled={busy} onClick={() => changeStatus(t.id, 'done')}>
                                                    {busy ? '…' : 'Done'}
                                                </button>
                                            )}
                                            <button className="danger" disabled={busy} onClick={() => remove(t.id)}>
                                                {busy ? '…' : 'Delete'}
                                            </button>
                                        </div>
                                    </li>
                                )
                            })}
                        </ul>
                    )}

                    <div className="pager">
                        <button disabled={page<=1 || loading} onClick={() => fetchPage(page-1)}>Prev</button>
                        <span>Сторінка {page} / {totalPages}</span>
                        <button disabled={page>=totalPages || loading} onClick={() => fetchPage(page+1)}>Next</button>
                    </div>
                </>
            )}
        </div>
    )
}
