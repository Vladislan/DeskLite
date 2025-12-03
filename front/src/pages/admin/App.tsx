import React, { useEffect, useState, useCallback } from 'react'
import { requireRole, logout } from '../../app/api/auth'
import OperatorApp from '../operator/App'
import {
    getAdminStats,
    type AdminStats,
    type AdminQAStat,
    listUsers,
    listUserTickets,
    type User,
    listOperatorSignups,
    approveOperatorSignup,
    type OperatorSignup,
    deleteUser,
    getOperatorProductivity,
    type OperatorProductivity,
} from '../../app/api/client'

import PasswordRecoveryRequestsCard from './PasswordRecoveryRequestsCard'
import OperatorPerformanceChart from './OperatorPerformanceGrid'

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

function RoleBadge({ role }: { role: User['role'] }) {
    const cls =
        role === 'admin' ? 'badge green' : role === 'operator' ? 'badge orange' : 'badge gray'
    return <span className={cls}>{role}</span>
}

export default function AdminApp() {
    const me = requireRole(['admin'])
    const meId = me?.id

    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const [stats, setStats] = useState<AdminStats | null>(null)

    const [users, setUsers] = useState<User[]>([])
    const [usersLoading, setUsersLoading] = useState(false)
    const [usersError, setUsersError] = useState<string | null>(null)
    const [openUserId, setOpenUserId] = useState<number | null>(null)
    const [tickets, setTickets] = useState<any[] | null>(null)
    const [ticketsLoading, setTicketsLoading] = useState(false)

    const [signups, setSignups] = useState<OperatorSignup[]>([])
    const [signupsLoading, setSignupsLoading] = useState(false)
    const [signupsError, setSignupsError] = useState<string | null>(null)

    const [showOpsChart, setShowOpsChart] = useState(false)
    const [opsChartDays, setOpsChartDays] = useState(30)
    const [opsData, setOpsData] = useState<OperatorProductivity[] | null>(null)
    const [opsLoading, setOpsLoading] = useState(false)

    const loadStats = useCallback(async () => {
        try {
            const s = await getAdminStats()
            setStats(s)
        } catch {
            setStats({ users: [], operators: [], qa: [] })
        }
    }, [])

    useEffect(() => {
        if (!meId) return
        loadStats()
    }, [meId, loadStats])

    const loadUsers = useCallback(async () => {
        try {
            setUsersLoading(true)
            setUsersError(null)
            const res = await listUsers(1, 100)
            setUsers(res.items ?? [])
        } catch (e: any) {
            setUsersError(e?.message ?? 'Failed to load users')
            setUsers([])
        } finally {
            setUsersLoading(false)
        }
    }, [])

    const loadSignups = useCallback(async () => {
        try {
            setSignupsLoading(true)
            setSignupsError(null)
            const rows = await listOperatorSignups()
            setSignups(rows)
        } catch (e: any) {
            setSignupsError(e?.message ?? 'Не вдалося завантажити заявки')
            setSignups([])
        } finally {
            setSignupsLoading(false)
        }
    }, [])

    const loadOpsChart = useCallback(
        async (days: number) => {
            setOpsLoading(true)
            try {
                const data = await getOperatorProductivity(days)
                setOpsData(data)
            } finally {
                setOpsLoading(false)
            }
        },
        [],
    )

    useEffect(() => {
        if (meId) {
            loadUsers()
            loadSignups()
        }
    }, [meId, loadUsers, loadSignups])

    useEffect(() => {
        if (showOpsChart) loadOpsChart(opsChartDays)
    }, [showOpsChart, opsChartDays, loadOpsChart])

    const toggleTickets = async (u: User) => {
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
    }

    const onApproveSignup = async (t: OperatorSignup) => {
        await approveOperatorSignup(t.id)
        await Promise.all([loadSignups(), loadUsers(), loadStats()])
    }

    const onDeleteUser = async (u: User) => {
        if (!window.confirm(`Видалити користувача ${u.email}?`)) return
        try {
            await deleteUser(u.id)
            await Promise.all([loadUsers(), loadStats()])
        } catch (e: any) {
            const msg =
                e?.response?.data?.detail ||
                e?.message ||
                'Не вдалося видалити користувача'
            alert(msg)
        }
    }

    if (!me) return null

    return (
        <div className="page">
            <header className="topbar">
                <div className="left" />
                <div className="brand-center">
                    <img src="/DeskLite_white.png" alt="DeskLite" className="brand-logo brand-dark" />
                    <img src="/DeskLite_black.png" alt="DeskLite" className="brand-logo brand-light" />
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

            <main className="container">
                {/* Desk оператора всередині адмінки */}
                <section className="card">
                    <h3>Desk</h3>
                    <OperatorApp modalRole="admin" hideHeader onTicketsChanged={loadStats} />
                </section>

                {/* Користувачі */}
                <section className="card">
                    <h3>Користувачі</h3>
                    {usersLoading && <div className="muted">Завантаження…</div>}
                    {usersError && <div className="muted">Помилка: {usersError}</div>}
                    {!usersLoading && !usersError && (
                        <div className="table-wrap">
                            <table className="table">
                                <thead>
                                <tr>
                                    <th style={{ width: 90 }}>ID</th>
                                    <th>Email</th>
                                    <th style={{ width: 160 }}>Роль</th>
                                    <th style={{ width: 260 }}>Дії</th>
                                </tr>
                                </thead>
                                <tbody>
                                {users.length === 0 ? (
                                    <tr>
                                        <td colSpan={4}>
                                            <span className="muted">Поки порожньо</span>
                                        </td>
                                    </tr>
                                ) : (
                                    users.map((u) => (
                                        <React.Fragment key={u.id}>
                                            <tr>
                                                <td>#{u.id}</td>
                                                <td>{u.email}</td>
                                                <td>
                                                    <RoleBadge role={u.role} />
                                                </td>
                                                <td>
                                                    <div className="actions" style={{ gap: 8 }}>
                                                        <button
                                                            className="btn sm"
                                                            onClick={() => toggleTickets(u)}
                                                        >
                                                            {openUserId === u.id
                                                                ? 'Сховати заявки'
                                                                : 'Показати заявки'}
                                                        </button>
                                                        <button
                                                            className="btn sm danger"
                                                            onClick={() => onDeleteUser(u)}
                                                        >
                                                            Видалити
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                            {openUserId === u.id && (
                                                <tr>
                                                    <td colSpan={4}>
                                                        {ticketsLoading ? (
                                                            <div className="muted small">
                                                                Заявки завантажуються…
                                                            </div>
                                                        ) : !tickets || tickets.length === 0 ? (
                                                            <div className="muted small">Заявок немає</div>
                                                        ) : (
                                                            <div
                                                                className="table-wrap"
                                                                style={{ marginTop: 8 }}
                                                            >
                                                                <table className="table">
                                                                    <thead>
                                                                    <tr>
                                                                        <th style={{ width: 90 }}>ID</th>
                                                                        <th>Назва</th>
                                                                        <th style={{ width: 160 }}>Статус</th>
                                                                        <th style={{ width: 160 }}>Пріоритет</th>
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
                                    ))
                                )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                {/* Заявки на операторів */}
                <section className="card">
                    <h3>Заявки на операторів</h3>
                    {signupsLoading && <div className="muted">Завантаження…</div>}
                    {signupsError && <div className="muted">Помилка: {signupsError}</div>}
                    {!signupsLoading && !signupsError && (
                        <div className="table-wrap">
                            <table className="table">
                                <thead>
                                <tr>
                                    <th style={{ width: 90 }}>ID</th>
                                    <th>Email</th>
                                    <th>ПІБ</th>
                                    <th>Телефон</th>
                                    <th style={{ width: 160 }}>Дії</th>
                                </tr>
                                </thead>
                                <tbody>
                                {signups.length === 0 ? (
                                    <tr>
                                        <td colSpan={5}>
                                            <span className="muted">Поки порожньо</span>
                                        </td>
                                    </tr>
                                ) : (
                                    signups.map((s) => (
                                        <tr key={s.id}>
                                            <td>#{s.id}</td>
                                            <td>{s.email}</td>
                                            <td>{s.full_name ?? '—'}</td>
                                            <td>{s.phone ?? '—'}</td>
                                            <td>
                                                <div className="actions">
                                                    <button
                                                        className="btn sm primary"
                                                        onClick={() => onApproveSignup(s)}
                                                    >
                                                        Схвалити
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                {/* заявки на відновлення паролю */}
                <PasswordRecoveryRequestsCard />

                {/* Оператори: таблиця / графік */}
                <section className="card">
                    <div className="between" style={{ marginBottom: 8 }}>
                        <h3>Оператори</h3>
                        <div className="actions" style={{ gap: 8 }}>
                            <label className="small">
                                Період:
                                <select
                                    value={opsChartDays}
                                    onChange={(e) => setOpsChartDays(Number(e.target.value))}
                                    disabled={!showOpsChart}
                                    style={{ marginLeft: 8 }}
                                >
                                    <option value={7}>7 днів</option>
                                    <option value={14}>14 днів</option>
                                    <option value={30}>30 днів</option>
                                    <option value={60}>60 днів</option>
                                </select>
                            </label>
                            <button
                                className="btn sm"
                                onClick={() => setShowOpsChart((v) => !v)}
                            >
                                {showOpsChart ? 'Показати таблицю' : 'Графік продуктивності'}
                            </button>
                            {showOpsChart && (
                                <button
                                    className="btn sm"
                                    onClick={() => loadOpsChart(opsChartDays)}
                                    disabled={opsLoading}
                                >
                                    Оновити
                                </button>
                            )}
                        </div>
                    </div>

                    {!showOpsChart ? (
                        <div className="table-wrap">
                            <table className="table">
                                <thead>
                                <tr>
                                    <th>Email</th>
                                    <th>In&nbsp;progress</th>
                                    <th>Done</th>
                                    <th>Canceled</th>
                                    <th>Сер. час вирішення</th>
                                </tr>
                                </thead>
                                <tbody>
                                {(stats?.operators ?? []).length === 0 ? (
                                    <tr>
                                        <td colSpan={5}>
                                            <span className="muted">Поки порожньо</span>
                                        </td>
                                    </tr>
                                ) : (
                                    stats!.operators.map((o) => {
                                        const avg = o.avg_resolution_minutes
                                        const slaBad = avg != null && avg > 60
                                        return (
                                            <tr
                                                key={o.email}
                                                className={slaBad ? 'row-sla-bad' : undefined}
                                            >
                                                <td>{o.email}</td>
                                                <td>
                                                    <span className="chip warn">{o.in_progress}</span>
                                                </td>
                                                <td>
                                                    <span className="chip ok">{o.done}</span>
                                                </td>
                                                <td>
                                                    <span className="chip danger">{o.canceled}</span>
                                                </td>
                                                <td>
                                                    {avg != null ? `${avg.toFixed(1)} хв` : '—'}
                                                </td>
                                            </tr>
                                        )
                                    })
                                )}
                                </tbody>
                            </table>
                        </div>
                    ) : opsLoading ? (
                        <div className="muted">Графік завантажується…</div>
                    ) : (
                        <OperatorPerformanceChart data={opsData ?? []} days={opsChartDays} />
                    )}
                </section>

                {/* QA */}
                <section className="card">
                    <h3>Питання користувачів (QA)</h3>
                    <div className="table-wrap">
                        <table className="table">
                            <thead>
                            <tr>
                                <th style={{ width: 90 }}>QID</th>
                                <th>Заголовок</th>
                                <th>Від кого</th>
                                <th style={{ width: 120 }}>Відповідей</th>
                                <th style={{ width: 220 }}>Остання відповідь</th>
                            </tr>
                            </thead>
                            {(stats?.qa ?? []).length === 0 ? (
                                <tbody>
                                <tr>
                                    <td colSpan={5}>
                                        <span className="muted">Поки порожньо</span>
                                    </td>
                                </tr>
                                </tbody>
                            ) : (
                                <tbody>
                                {(stats!.qa as AdminQAStat[]).map((row) => (
                                    <tr key={row.question_id}>
                                        <td>#{row.question_id}</td>
                                        <td>{row.title}</td>
                                        <td>{row.user_email}</td>
                                        <td>{row.answers}</td>
                                        <td>{row.last_answer_at ?? '—'}</td>
                                    </tr>
                                ))}
                                </tbody>
                            )}
                        </table>
                    </div>
                </section>
            </main>
        </div>
    )
}
