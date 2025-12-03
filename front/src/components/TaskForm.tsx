import { useState } from 'react'
import { createTask } from '../app/api/client'
type Props = { onCreated?: () => void }

export default function TaskForm({ onCreated }: Props) {
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [deadline, setDeadline] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const canSubmit = title.trim().length > 0 && !loading

    const submit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!canSubmit) return
        setLoading(true)
        setError(null)
        try {
            await createTask({
                title: title.trim(),
                description: description.trim() || undefined,
                deadline: deadline || undefined,
            })
            setTitle(''); setDescription(''); setDeadline('')
            onCreated?.()
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Не вдалося створити задачу')
        } finally {
            setLoading(false)
        }
    }

    return (
        <form onSubmit={submit} className="card">
            <h2>Створити задачу</h2>

            <label>
                Назва
                <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Коротка назва"
                    required
                />
            </label>

            <label>
                Опис
                <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Необов’язково"
                />
            </label>

            <label>
                Дедлайн (YYYY-MM-DD)
                <input
                    type="date"
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                />
            </label>

            {error && <div className="muted small" style={{color:'#fca5a5'}}>{error}</div>}

            <button disabled={!canSubmit}>{loading ? 'Збереження…' : 'Додати'}</button>
        </form>
    )
}
