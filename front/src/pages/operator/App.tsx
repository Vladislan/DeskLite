// src/pages/operator/app.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { requireRole, logout } from '../../app/api/auth'
import { listTasks, updateTaskStatus, patchTicket, hardDeleteTicket } from '../../app/api/client'
import type { Task, TaskStatus } from '../../../types'
import OperatorQuestionsCard from './QuestionsCard'
import TicketDetailsModal from './TicketDetailsModal'
import AdminFeedbackCard from './AdminFeedbackCard'

type ModalRole = 'operator' | 'admin'

function useTheme(): ['light' | 'dark', (t: 'light' | 'dark') => void] {
    const initial = (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
    const [theme, setTheme] = React.useState<'light' | 'dark'>(initial)
    React.useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme)
        localStorage.setItem('theme', theme)
    }, [theme])
    return [theme, setTheme]
}
function ThemeSwitch() {
    const [theme, setTheme] = useTheme()
    const next = theme === 'light' ? 'dark' : 'light'
    return (
        <button className="btn sm white" onClick={() => setTheme(next)} title="Змінити тему">
            {theme === 'light' ? '🌙 Нічний' : '☀️ Денний'}
        </button>
    )
}

/** хелпер: визначаємо чи тікет — це “заявка на оператора” */
function isOperatorSignup(t: any): boolean {
    const topicHit = String(t?.topic ?? '').toLowerCase() === 'operator_signup'
    const catHit = String(t?.category ?? '').toLowerCase() === 'mgmt'
    const statusHit = String(t?.status ?? '').toLowerCase() === 'pending_admin'
    const title = String(t?.title ?? '').toLowerCase()
    const titleHit =
        title.includes('реєстрацію оператора') ||
        title.includes('registration of operator') ||
        title.includes('operator signup')
    // якщо це службовий “операторський” запит — ховаємо від оператора
    return topicHit || (catHit && titleHit) || statusHit
}

export default function OperatorApp({
                                        modalRole = 'operator',
                                        hideHeader = false,
                                        onTicketsChanged,
                                    }: {
    modalRole?: ModalRole
    hideHeader?: boolean
    /** 🔹 колбек, який викликається після змін тікетів (для оновлення SLA в адмінці) */
    onTicketsChanged?: () => void
}) {
    const me = requireRole(['operator', 'admin'])
    const meId = (me?.id ?? undefined) as number | undefined

    // гарантуємо атрибут теми на першому рендері
    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const [items, setItems] = useState<Task[]>([])
    const [openTicket, setOpenTicket] = useState<Task | null>(null)
    const didInit = useRef(false)

    const load = useCallback(async () => {
        const res = await listTasks(1, 100)
        let rows = res.items as any[]

        // оператор НЕ бачить заявки на реєстрацію оператора
        if (modalRole === 'operator') {
            rows = rows.filter((t) => !isOperatorSignup(t))
        }

        setItems(rows as Task[])
    }, [modalRole])

    useEffect(() => {
        if (!meId) return
        if (didInit.current) return
        didInit.current = true
        load()
    }, [meId, load])

    if (!me) return null

    const move = async (id: Task['id'], s: TaskStatus) => {
        const nId = typeof id === 'string' ? Number(id) : id
        const t = items.find(
            (x) => (typeof x.id === 'string' ? Number(x.id) : x.id) === nId
        )
        if (s === 'in_progress' && !t?.assignee_id && meId) {
            await patchTicket(nId, { status: s, assignee_id: meId })
        } else {
            await updateTaskStatus(nId, s)
        }
        await load()
        onTicketsChanged?.() // 🔹 оновити SLA / статистику, якщо треба
    }

    const badge = (s: TaskStatus) => {
        const cls =
            s === 'done'
                ? 'badge green'
                : s === 'in_progress'
                    ? 'badge orange'
                    : s === 'canceled'
                        ? 'badge danger'
                        : s === 'blocked'
                            ? 'badge warn'
                            : s === 'triage'
                                ? 'badge blue'
                                : 'badge gray'
        return <span className={cls}>{String(s)}</span>
    }

    // ШТАМПИ: правильні шляхи
    const stampSmall =
        modalRole === 'admin'
            ? '/img/DeskLite_Admin_stamp_v2.png'
            : '/img/DeskLite_Operator_stamp_v2.png'

    return (
        <div className="page">
            {!hideHeader && (
                <header className="topbar">
                    <div className="left" />
                    <div className="brand-center">
                        <img
                            src="/DeskLite_white.png"
                            alt="DeskLite"
                            className="brand-logo brand-dark"
                        />
                        <img
                            src="/DeskLite_black.png"
                            alt="DeskLite"
                            className="brand-logo brand-light"
                        />
                    </div>
                    <div className="right">
                        <ThemeSwitch />
                        <span className="user">{me.email}</span>
                        <button
                            className="btn sm white"
                            onClick={() => {
                                logout()
                                location.href = '/login.html'
                            }}
                        >
                            Вийти
                        </button>
                    </div>
                </header>
            )}

            <main className="container">
                <section className="card">
                    <h3>Черга заявок</h3>
                    {items.length === 0 ? (
                        <div className="muted">Порожньо</div>
                    ) : (
                        <div className="table-wrap">
                            <table className="table">
                                <thead>
                                <tr>
                                    <th style={{ width: 90 }}>ID</th>
                                    <th>Назва</th>
                                    <th style={{ width: 160 }}>Статус</th>
                                    <th style={{ width: 380 }}>Дії</th>
                                </tr>
                                </thead>
                                <tbody>
                                {items.map((t) => {
                                    const nId =
                                        typeof t.id === 'string'
                                            ? Number(t.id)
                                            : t.id
                                    return (
                                        <tr key={String(t.id)}>
                                            <td>#{String(t.id)}</td>
                                            <td>
                                                {t.title}
                                                {'dept' in t || 'topic' in t ? (
                                                    <div
                                                        className="small"
                                                        style={{
                                                            color: 'var(--muted)',
                                                        }}
                                                    >
                                                        {(t as any).dept
                                                            ? labelDept(
                                                                (t as any).dept,
                                                            )
                                                            : ''}
                                                        {(t as any).topic
                                                            ? ` • ${(t as any)
                                                                .topic}`
                                                            : ''}
                                                    </div>
                                                ) : null}
                                            </td>
                                            <td>{badge(t.status)}</td>
                                            <td>
                                                <div className="actions">
                                                    <button
                                                        className="btn sm"
                                                        onClick={() =>
                                                            setOpenTicket(t)
                                                        }
                                                    >
                                                        Відкрити
                                                    </button>
                                                    <button
                                                        className="btn sm warn"
                                                        onClick={() =>
                                                            move(
                                                                nId,
                                                                'in_progress',
                                                            )
                                                        }
                                                    >
                                                        В роботу
                                                    </button>
                                                    <button
                                                        className="btn sm success"
                                                        onClick={() =>
                                                            move(
                                                                nId,
                                                                'done',
                                                            )
                                                        }
                                                    >
                                                        Закрити
                                                    </button>
                                                    <button
                                                        className="btn sm danger"
                                                        onClick={async () => {
                                                            if (
                                                                !confirm(
                                                                    `Видалити заявку #${nId}? Операція незворотна.`,
                                                                )
                                                            )
                                                                return
                                                            await hardDeleteTicket(
                                                                nId,
                                                            )
                                                            await load()
                                                            onTicketsChanged?.()
                                                        }}
                                                    >
                                                        Видалити
                                                    </button>
                                                    {t.status === 'done' && (
                                                        <img
                                                            src={stampSmall}
                                                            className="stamp-badge"
                                                            alt=""
                                                        />
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                <section className="card">
                    <OperatorQuestionsCard />
                </section>

                {/* Новий блок: рекомендації адміністратора */}
                <section className="card">
                    <AdminFeedbackCard />
                </section>
            </main>

            {openTicket && (
                <TicketDetailsModal
                    role={modalRole}
                    ticket={openTicket}
                    onClose={() => setOpenTicket(null)}
                    reload={async () => {
                        await load()
                        onTicketsChanged?.()
                    }}
                />
            )}
        </div>
    )
}

function labelDept(d?: string) {
    switch (d) {
        case 'dev':
            return 'Відділ розробки'
        case 'impl':
            return 'Відділ впровадження'
        case 'info':
            return 'Інформаційний відділ'
        case 'mgmt':
            return 'Управління'
        default:
            return ''
    }
}
