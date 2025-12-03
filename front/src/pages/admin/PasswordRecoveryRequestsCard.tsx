import React, { useEffect, useState } from 'react'
import { api } from '../../app/api/client'

interface RecoveryRequest {
    id: number
    email: string
    status: string
    reset_url?: string
}

export default function PasswordRecoveryRequestsCard() {
    const [items, setItems] = useState<RecoveryRequest[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const load = async () => {
        setLoading(true); setError(null)
        try {
            const r = await api.get<RecoveryRequest[]>('/auth/password-recovery-requests')
            setItems(r.data)
        } catch (err: any) {
            const detail = err?.response?.data?.detail
            setError(detail || err?.message || 'Не вдалося завантажити заявки на відновлення паролю')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load()
    }, [])

    const sendLink = async (id: number) => {
        try {
            const r = await api.post<{ reset_url: string }>(`/auth/password-recovery-requests/${id}/send-link`)
            const url = r.data.reset_url

            // одразу покажемо лінк
            alert(`Посилання на відновлення:\n${url}`)

            // оновлюємо список із бекенду, щоб підтягнути оновлений статус (done)
            await load()
        } catch (err: any) {
            const detail = err?.response?.data?.detail
            setError(detail || err?.message || 'Не вдалося надіслати посилання')
        }
    }

    return (
        <div className="card">
            <div className="card__head">
                <h3>Заявки на відновлення паролю</h3>
                <button className="btn ghost sm" onClick={load} disabled={loading}>
                    Оновити
                </button>
            </div>
            {error && <div className="muted small" style={{ color: '#fca5a5' }}>{error}</div>}
            {items.length === 0 && !loading && (
                <div className="muted small">Поки немає заявок.</div>
            )}
            <div className="table-wrap">
                <table className="table">
                    <thead>
                    <tr>
                        <th>ID</th>
                        <th>Email</th>
                        <th>Статус</th>
                        <th>Дія</th>
                    </tr>
                    </thead>
                    <tbody>
                    {items.map(it => {
                        // заявка вважається обробленою, якщо статус не pending_admin
                        const processed = it.status !== 'pending_admin'
                        return (
                            <tr
                                key={it.id}
                                style={processed ? { opacity: 0.7 } : undefined}
                            >
                                <td>#{it.id}</td>
                                <td>{it.email}</td>
                                <td>{it.status}</td>
                                <td>
                                    <button
                                        className="btn xs"
                                        onClick={() => sendLink(it.id)}
                                        disabled={processed}
                                    >
                                        {processed ? 'Оброблено' : 'Надіслати посилання'}
                                    </button>
                                </td>
                            </tr>
                        )
                    })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
