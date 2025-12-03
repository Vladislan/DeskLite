import React, { useCallback, useEffect, useState } from 'react'
import { listUsers, listUserTickets, type User } from '../../app/api/client'

function RoleBadge({ role }: { role: User['role'] }) {
    const cls = role === 'admin' ? 'badge green' : role === 'operator' ? 'badge orange' : 'badge gray'
    return <span className={cls}>{role}</span>
}

export default function UsersPanel() {
    const [users, setUsers] = useState<User[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [openUserId, setOpenUserId] = useState<number | null>(null)
    const [tickets, setTickets] = useState<any[] | null>(null)
    const [ticketsLoading, setTicketsLoading] = useState(false)

    const loadUsers = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)
            const res = await listUsers(1, 100)
            setUsers(res.items ?? [])
        } catch (e: any) {
            setError(e?.message ?? 'Failed to load users')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { loadUsers() }, [loadUsers])

    const toggleTickets = useCallback(async (u: User) => {
        if (openUserId === u.id) {
            setOpenUserId(null)
            setTickets(null)
            return
        }
        setOpenUserId(u.id)
        setTicketsLoading(true)
        try {
            const rows = await listUserTickets(u.id, 100)
            setTickets(rows ?? [])
        } finally {
            setTicketsLoading(false)
        }
    }, [openUserId])

    return (
        <section className="card">
            <h3>Users</h3>

            {loading && <div className="muted">Завантаження…</div>}
            {error && <div className="muted">Помилка: {error}</div>}
            {!loading && !error && users.length === 0 && <div className="muted">Користувачів поки немає</div>}

            {users.length > 0 && (
                <div className="table-wrap">
                    <table className="table">
                        <thead>
                        <tr>
                            <th style={{width:90}}>ID</th>
                            <th>Email</th>
                            <th style={{width:160}}>Роль</th>
                            <th style={{width:220}}>Дії</th>
                        </tr>
                        </thead>
                        <tbody>
                        {users.map(u => (
                            <React.Fragment key={u.id}>
                                <tr>
                                    <td>#{u.id}</td>
                                    <td>{u.email}</td>
                                    <td><RoleBadge role={u.role} /></td>
                                    <td>
                                        <div className="actions">
                                            <button className="btn sm" onClick={() => toggleTickets(u)}>
                                                {openUserId === u.id ? 'Сховати заявки' : 'Показати заявки'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>

                                {openUserId === u.id && (
                                    <tr>
                                        <td colSpan={4}>
                                            {ticketsLoading ? (
                                                <div className="muted small">Заявки завантажуються…</div>
                                            ) : !tickets || tickets.length === 0 ? (
                                                <div className="muted small">Заявок немає</div>
                                            ) : (
                                                <div className="table-wrap" style={{marginTop:8}}>
                                                    <table className="table">
                                                        <thead>
                                                        <tr>
                                                            <th style={{width:90}}>ID</th>
                                                            <th>Назва</th>
                                                            <th style={{width:160}}>Статус</th>
                                                            <th style={{width:160}}>Пріоритет</th>
                                                        </tr>
                                                        </thead>
                                                        <tbody>
                                                        {tickets.map((t: any) => (
                                                            <tr key={t.id}>
                                                                <td>#{t.id}</td>
                                                                <td>{t.title}</td>
                                                                <td>{String(t.status)}</td>
                                                                <td>{String(t.priority ?? '')}</td>
                                                            </tr>
                                                        ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    )
}
