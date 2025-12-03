import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
    listQuestions, listAnswers, answerQuestion, closeQuestion,
    type Question, type Answer, type QStatus
} from '../../app/api/client'
import { requireRole } from '../../app/api/auth'

type RowOpen = Record<number, boolean>

const statusLabel: Record<QStatus, string> = {
    new: 'new',
    answered: 'answered',
    closed: 'closed',
}

export default function OperatorQuestionsCard() {
    // тільки operator/admin
    requireRole(['operator', 'admin'])

    const [tab, setTab] = useState<QStatus | 'all'>('new')
    const [rows, setRows] = useState<Question[]>([])
    const [open, setOpen] = useState<RowOpen>({})
    const [answers, setAnswers] = useState<Record<number, Answer[]>>({})
    const [draft, setDraft] = useState<Record<number, string>>({})
    const [loading, setLoading] = useState(false)
    const didInit = useRef(false)

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const params = tab === 'all' ? {} : { status: tab }
            const data = await listQuestions(params as any)
            setRows(data ?? [])
        } finally {
            setLoading(false)
        }
    }, [tab])

    useEffect(() => {
        if (didInit.current) return
        didInit.current = true
        load()
    }, [load])

    useEffect(() => {
        load()
    }, [tab, load])

    const toggleOpen = async (qid: number) => {
        const next = !open[qid]
        setOpen(prev => ({ ...prev, [qid]: next }))
        if (next && !answers[qid]) {
            const ans = await listAnswers(qid)
            setAnswers(prev => ({ ...prev, [qid]: ans }))
        }
    }

    const submitAnswer = async (qid: number) => {
        const text = (draft[qid] ?? '').trim()
        if (!text) return
        const a = await answerQuestion(qid, text)
        setAnswers(prev => ({ ...prev, [qid]: [...(prev[qid] ?? []), a] }))
        setDraft(prev => ({ ...prev, [qid]: '' }))
        // якщо відповідь створено — статус питання стає answered → оновимо список
        await load()
    }

    const doClose = async (qid: number) => {
        await closeQuestion(qid)
        await load()
    }

    const filtered = useMemo(() => rows, [rows])

    return (
        <section className="card">
            <div className="row between center">
                <h3>Питання користувачів (Q&A)</h3>
                <div className="tabs">
                    <button className={`btn sm ${tab === 'new' ? 'primary' : 'ghost'}`} onClick={() => setTab('new')}>New</button>
                    <button className={`btn sm ${tab === 'answered' ? 'primary' : 'ghost'}`} onClick={() => setTab('answered')}>Answered</button>
                    <button className={`btn sm ${tab === 'closed' ? 'primary' : 'ghost'}`} onClick={() => setTab('closed')}>Closed</button>
                    <button className={`btn sm ${tab === 'all' ? 'primary' : 'ghost'}`} onClick={() => setTab('all')}>All</button>
                </div>
            </div>

            {loading ? (
                <div className="muted">Завантаження…</div>
            ) : filtered.length === 0 ? (
                <div className="muted">Поки порожньо</div>
            ) : (
                <div className="table-wrap">
                    <table className="table">
                        <thead>
                        <tr>
                            <th style={{ width: 80 }}>QID</th>
                            <th>Заголовок</th>
                            <th style={{ width: 200 }}>Статус</th>
                            <th style={{ width: 240 }}>Дії</th>
                        </tr>
                        </thead>
                        <tbody>
                        {filtered.map(q => (
                            <React.Fragment key={q.id}>
                                <tr>
                                    <td>#{q.id}</td>
                                    <td>
                                        <div className="col">
                                            <div>{q.title}</div>
                                            <div className="muted small">{q.content}</div>
                                        </div>
                                    </td>
                                    <td>
                      <span className={
                          q.status === 'new' ? 'badge blue'
                              : q.status === 'answered' ? 'badge green'
                                  : 'badge gray'
                      }>
                        {statusLabel[q.status]}
                      </span>
                                    </td>
                                    <td>
                                        <div className="actions">
                                            <button className="btn sm" onClick={() => toggleOpen(q.id)}>
                                                {open[q.id] ? 'Сховати' : 'Показати'} відповіді
                                            </button>
                                            {q.status !== 'closed' && (
                                                <button className="btn sm ghost" onClick={() => doClose(q.id)}>
                                                    Закрити питання
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>

                                {open[q.id] && (
                                    <tr>
                                        <td colSpan={4}>
                                            {/* список відповідей */}
                                            <div className="table-wrap" style={{ marginTop: 8 }}>
                                                {(answers[q.id] ?? []).length === 0 ? (
                                                    <div className="muted small">Відповідей поки немає</div>
                                                ) : (
                                                    <table className="table small">
                                                        <thead>
                                                        <tr>
                                                            <th style={{ width: 90 }}>ID</th>
                                                            <th>Відповідь</th>
                                                            <th style={{ width: 200 }}>Час</th>
                                                        </tr>
                                                        </thead>
                                                        <tbody>
                                                        {(answers[q.id] ?? []).map(a => (
                                                            <tr key={a.id}>
                                                                <td>#{a.id}</td>
                                                                <td>{a.content}</td>
                                                                <td>{new Date(a.created_at).toLocaleString()}</td>
                                                            </tr>
                                                        ))}
                                                        </tbody>
                                                    </table>
                                                )}
                                            </div>

                                            {/* форма відповіді */}
                                            {q.status !== 'closed' && (
                                                <div style={{ marginTop: 8 }}>
                            <textarea
                                className="input"
                                placeholder="Напишіть відповідь…"
                                rows={3}
                                value={draft[q.id] ?? ''}
                                onChange={(e) => setDraft(prev => ({ ...prev, [q.id]: e.target.value }))}
                                style={{ marginBottom: 8 }}
                            />
                                                    <div className="actions">
                                                        <button
                                                            className="btn primary sm"
                                                            disabled={!String(draft[q.id] ?? '').trim()}
                                                            onClick={() => submitAnswer(q.id)}
                                                        >
                                                            Відповісти
                                                        </button>
                                                    </div>
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
