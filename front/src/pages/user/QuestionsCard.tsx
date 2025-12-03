import React, { useEffect, useState } from 'react'
import { requireRole } from '../../app/api/auth'
import {
    createQuestion, listQuestions, listAnswers,
    type Question, type Answer
} from '../../app/api/client'

export default function UserQuestionsCard() {
    // тільки юзер (адмін/оператор теж можуть, але сенс у юзера)
    requireRole(['user', 'admin', 'operator'])

    const [myQ, setMyQ] = useState<Question[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [title, setTitle] = useState('')
    const [content, setContent] = useState('')

    const [openQ, setOpenQ] = useState<Question | null>(null)
    const [answers, setAnswers] = useState<Answer[]>([])

    const loadMine = async () => {
        try {
            setLoading(true)
            setError(null)
            // бек на стороні користувача повертає ТІЛЬКИ його питання
            const rows = await listQuestions({ limit: 100 })
            setMyQ(rows.sort(
                (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            ))
        } catch (e: any) {
            setError(e?.message ?? 'Не вдалося завантажити питання')
        } finally {
            setLoading(false)
        }
    }

    const create = async () => {
        if (!title.trim() || !content.trim()) return
        await createQuestion({ title: title.trim(), content: content.trim() })
        setTitle(''); setContent('')
        await loadMine()
    }

    const open = async (q: Question) => {
        setOpenQ(q)
        const rows = await listAnswers(q.id)
        setAnswers(rows)
    }

    useEffect(() => {
        loadMine()
    }, [])

    return (
        <section className="card">
            <h3>Мої питання</h3>

            {/* форма створення */}
            <div className="subcard" style={{marginBottom:10}}>
                <input
                    className="input"
                    placeholder="Заголовок"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    style={{marginBottom:6}}
                />
                <textarea
                    className="input"
                    rows={3}
                    placeholder="Опишіть ваше питання…"
                    value={content}
                    onChange={e => setContent(e.target.value)}
                />
                <div className="actions" style={{marginTop:6}}>
                    <button className="btn sm success" disabled={!title.trim() || !content.trim()} onClick={create}>
                        Створити питання
                    </button>
                </div>
            </div>

            {error && <div className="muted">Помилка: {error}</div>}
            {loading && <div className="muted">Завантаження…</div>}

            {!loading && (
                <div className="table-wrap">
                    <table className="table">
                        <thead>
                        <tr>
                            <th style={{width:90}}>QID</th>
                            <th>Заголовок</th>
                            <th style={{width:140}}>Статус</th>
                            <th style={{width:160}}>Дії</th>
                        </tr>
                        </thead>
                        <tbody>
                        {myQ.length === 0 ? (
                            <tr><td colSpan={4}><span className="muted">Поки порожньо</span></td></tr>
                        ) : myQ.map(q => (
                            <tr key={q.id}>
                                <td>#{q.id}</td>
                                <td>{q.title}</td>
                                <td>
                  <span className={
                      q.status === 'new' ? 'badge orange' :
                          q.status === 'answered' ? 'badge green' : 'badge gray'
                  }>
                    {q.status}
                  </span>
                                </td>
                                <td>
                                    <button className="btn sm" onClick={() => open(q)}>Відкрити</button>
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* деталі + відповіді */}
            {openQ && (
                <div className="subcard" style={{marginTop:12}}>
                    <div className="row" style={{marginBottom:8}}>
                        <div><b>Q#{openQ.id}</b> &nbsp; {openQ.title}</div>
                        <div>
              <span className={
                  openQ.status === 'new' ? 'badge orange' :
                      openQ.status === 'answered' ? 'badge green' : 'badge gray'
              }>
                {openQ.status}
              </span>
                        </div>
                    </div>

                    <div className="muted" style={{marginBottom:10}}>{openQ.content}</div>

                    <div className="table-wrap">
                        <table className="table">
                            <thead>
                            <tr>
                                <th style={{width:90}}>AID</th>
                                <th>Відповідь</th>
                                <th style={{width:200}}>Коли</th>
                            </tr>
                            </thead>
                            <tbody>
                            {answers.length === 0 ? (
                                <tr><td colSpan={3}><span className="muted">Відповідей ще немає</span></td></tr>
                            ) : answers.map(a => (
                                <tr key={a.id}>
                                    <td>#{a.id}</td>
                                    <td>{a.content}</td>
                                    <td>{new Date(a.created_at).toLocaleString()}</td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="actions" style={{marginTop:6}}>
                        <button className="btn sm ghost" onClick={() => setOpenQ(null)}>Закрити панель</button>
                    </div>
                </div>
            )}
        </section>
    )
}
