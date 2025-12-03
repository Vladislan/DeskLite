// src/pages/operator/AdminFeedbackCard.tsx
import React, { useCallback, useEffect, useState } from 'react'
import {
    listMyOperatorFeedback,
    type AdminOperatorFeedback,
} from '../../app/api/client'

export default function AdminFeedbackCard() {
    const [items, setItems] = useState<AdminOperatorFeedback[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const load = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)
            const data = await listMyOperatorFeedback()
            setItems(data)
        } catch (e: any) {
            setError(
                e?.response?.data?.detail ??
                e?.message ??
                'Не вдалося завантажити рекомендації',
            )
            setItems([])
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        load()
    }, [load])

    return (
        <div>
            <div className="between" style={{ marginBottom: 8 }}>
                <h3>Рекомендації адміністратора</h3>
                <button className="btn sm" onClick={load} disabled={loading}>
                    Оновити
                </button>
            </div>

            {loading && <div className="muted">Завантаження…</div>}
            {error && <div className="muted">Помилка: {error}</div>}

            {!loading && !error && (
                <div className="table-wrap">
                    <table className="table">
                        <thead>
                        <tr>
                            <th style={{ width: 160 }}>Отримано</th>
                            <th style={{ width: 220 }}>Від</th>
                            <th>Коментар</th>
                        </tr>
                        </thead>
                        <tbody>
                        {items.length === 0 ? (
                            <tr>
                                <td colSpan={3}>
                                        <span className="muted">
                                            Поки немає рекомендацій
                                        </span>
                                </td>
                            </tr>
                        ) : (
                            items.map((row) => (
                                <tr key={row.id}>
                                    <td>
                                            <span className="small">
                                                {new Date(
                                                    row.created_at,
                                                ).toLocaleString()}
                                            </span>
                                    </td>
                                    <td>
                                        {row.author_email ??
                                            'Адміністратор'}
                                    </td>
                                    <td>{row.message}</td>
                                </tr>
                            ))
                        )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
