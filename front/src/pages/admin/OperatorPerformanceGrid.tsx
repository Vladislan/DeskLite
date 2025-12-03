// src/pages/admin/OperatorPerformanceGrid.tsx
import React, { useMemo, useState, useCallback } from 'react'
import type {
    OperatorProductivity,
    OperatorSeriesPoint,
} from '../../app/api/client'
import { sendOperatorFeedback } from '../../app/api/client'

type Props = {
    data: OperatorProductivity[]
    /** Варіант діапазону: або days (поденно), або hours (погодинно) */
    days?: number
    hours?: number
    /** Метрика відображення: 'count' | 'avg' */
    metric?: 'count' | 'avg'
}

function buildDayRange(days: number): string[] {
    const out: string[] = []
    const now = new Date()
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(now)
        d.setDate(now.getDate() - i)
        out.push(d.toISOString().slice(0, 10))
    }
    return out
}

function buildHourRange(hours: number): string[] {
    const out: string[] = []
    const now = new Date()
    for (let i = hours - 1; i >= 0; i--) {
        const d = new Date(now)
        d.setHours(now.getHours() - i, 0, 0, 0)
        out.push(d.toISOString().slice(0, 13) + ':00') // 'YYYY-MM-DD HH:00'
    }
    return out
}

function mergeSeriesCount(range: string[], series: OperatorSeriesPoint[]): number[] {
    const m = new Map(series.map(s => [s.date, s.count]))
    return range.map(d => m.get(d) ?? 0)
}
function mergeSeriesAvg(range: string[], series: OperatorSeriesPoint[]): number[] {
    const m = new Map(series.map(s => [s.date, s.avg_minutes ?? 0]))
    return range.map(d => (m.get(d) ?? 0))
}

type MiniChartProps = {
    label: string
    ys: number[]
    range: string[]
    metric: 'count' | 'avg'
    onComment?: () => void
}

function MiniChart({ label, ys, range, metric, onComment }: MiniChartProps) {
    const padding = { top: 8, right: 8, bottom: 18, left: 30 }
    const W = 360, H = 150
    const innerW = W - padding.left - padding.right
    const innerH = H - padding.top - padding.bottom

    const maxY = Math.max(1, ...ys)
    const x = (i: number) =>
        padding.left + (i / Math.max(1, range.length - 1)) * innerW
    const y = (v: number) =>
        padding.top + innerH - (v / maxY) * innerH
    const path = ys
        .map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(2)} ${y(v).toFixed(2)}`)
        .join(' ')

    const total = ys.reduce((s, v) => s + v, 0)
    const last7 = ys.slice(-7).reduce((s, v) => s + v, 0)

    return (
        <div
            className="card"
            style={{
                padding: '10px 12px',
                position: 'relative',
                overflow: 'hidden',
            }}
        >
            <div
                className="between"
                style={{ marginBottom: 6, alignItems: 'center', gap: 8 }}
            >
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <strong style={{ fontSize: 14 }}>{label}</strong>
                    <div className="muted small">
                        {metric === 'count'
                            ? <>заявок: за період {total} • останні 7 дн/год: {last7}</>
                            : <>сер. хв: за період {total.toFixed(1)} • останні 7 відр.: {last7.toFixed(1)}</>
                        }
                    </div>
                </div>
                {onComment && (
                    <button
                        type="button"
                        className="btn sm"
                        style={{ fontSize: 11, padding: '4px 10px', whiteSpace: 'nowrap' }}
                        onClick={onComment}
                    >
                        Коментар
                    </button>
                )}
            </div>
            <svg
                viewBox={`0 0 ${W} ${H}`}
                width="100%"
                height={H}
                role="img"
                aria-label={`Продуктивність: ${label}`}
                style={{ color: 'var(--fg)' }}
            >
                {/* axes */}
                <line
                    x1={padding.left}
                    y1={padding.top}
                    x2={padding.left}
                    y2={H - padding.bottom}
                    stroke="currentColor"
                    opacity="0.25"
                />
                <line
                    x1={padding.left}
                    y1={H - padding.bottom}
                    x2={W - padding.right}
                    y2={H - padding.bottom}
                    stroke="currentColor"
                    opacity="0.25"
                />
                {/* y grid */}
                {[0, 0.5, 1].map((p, idx) => {
                    const yy = padding.top + innerH - p * innerH
                    const val = Math.round(p * maxY)
                    return (
                        <g key={idx}>
                            <line
                                x1={padding.left}
                                y1={yy}
                                x2={W - padding.right}
                                y2={yy}
                                stroke="currentColor"
                                opacity="0.08"
                            />
                            <text
                                x={padding.left - 6}
                                y={yy}
                                textAnchor="end"
                                dominantBaseline="middle"
                                fontSize="10"
                                opacity="0.6"
                            >
                                {val}
                            </text>
                        </g>
                    )
                })}
                {/* x labels: старт/середина/кінець */}
                {[0, Math.floor((range.length - 1) / 2), range.length - 1].map((i) => (
                    <text
                        key={i}
                        x={x(i)}
                        y={H - 4}
                        textAnchor="middle"
                        fontSize="10"
                        opacity="0.6"
                    >
                        {range[i]?.slice(5)}
                    </text>
                ))}
                {/* line */}
                <path
                    d={path}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                />
                {/* points */}
                {ys.map((v, i) => (
                    <circle key={i} cx={x(i)} cy={y(v)} r={2.3} />
                ))}
            </svg>
        </div>
    )
}

type CommentTarget = {
    operatorId: number
    email: string
}

export default function OperatorPerformanceGrid({
                                                    data,
                                                    days = 30,
                                                    hours,
                                                    metric = 'count',
                                                }: Props) {
    const hourly = !!hours || days <= 1
    const range = useMemo(
        () => (hourly ? buildHourRange(hours ?? 24) : buildDayRange(days)),
        [hourly, hours, days],
    )

    const prepared = useMemo(
        () =>
            data.map((op) => {
                const email = op.email || `#${op.operator_id}`
                const ys =
                    metric === 'count'
                        ? mergeSeriesCount(range, op.series || [])
                        : mergeSeriesAvg(range, op.series || [])
                return { email, ys, operatorId: op.operator_id }
            }),
        [data, range, metric],
    )

    const [commentTarget, setCommentTarget] = useState<CommentTarget | null>(null)
    const [commentText, setCommentText] = useState('')
    const [sending, setSending] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const closeModal = useCallback(() => {
        if (sending) return
        setCommentTarget(null)
        setCommentText('')
        setError(null)
    }, [sending])

    const handleSubmit = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault()
            if (!commentTarget) return
            const msg = commentText.trim()
            if (!msg) {
                setError('Коментар порожній')
                return
            }
            setSending(true)
            setError(null)
            try {
                await sendOperatorFeedback(commentTarget.operatorId, msg)
                closeModal()
                alert('Коментар надіслано оператору')
            } catch (err: any) {
                const msgErr =
                    err?.response?.data?.detail ||
                    err?.message ||
                    'Не вдалося надіслати коментар'
                setError(msgErr)
            } finally {
                setSending(false)
            }
        },
        [commentTarget, commentText, closeModal],
    )

    if (!prepared.length) {
        return <div className="muted">Немає даних за обраний період</div>
    }

    return (
        <>
            <div
                className="grid"
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                    gap: 12,
                }}
            >
                {prepared.map((op) => (
                    <MiniChart
                        key={`${op.email}-${op.operatorId}`}
                        label={op.email}
                        ys={op.ys}
                        range={range}
                        metric={metric}
                        onComment={() =>
                            setCommentTarget({
                                operatorId: op.operatorId,
                                email: op.email,
                            })
                        }
                    />
                ))}
            </div>

            {commentTarget && (
                <div
                    style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0,0,0,0.45)',
                        backdropFilter: 'blur(4px)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 50,
                    }}
                    onClick={closeModal}
                >
                    <div
                        className="card"
                        style={{
                            maxWidth: 520,
                            width: '90%',
                            padding: '18px 20px 16px',
                            borderRadius: 18,
                            boxShadow: '0 18px 60px rgba(0,0,0,0.65)',
                            border: '1px solid rgba(255,255,255,0.14)',
                            background: 'var(--panel)',
                            position: 'relative',
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <button
                            type="button"
                            onClick={closeModal}
                            style={{
                                position: 'absolute',
                                top: 10,
                                right: 12,
                                border: 'none',
                                background: 'transparent',
                                color: 'var(--muted)',
                                cursor: sending ? 'default' : 'pointer',
                                fontSize: 16,
                            }}
                            disabled={sending}
                            aria-label="Закрити"
                        >
                            ✕
                        </button>
                        <div style={{ marginBottom: 10 }}>
                            <div
                                style={{
                                    fontSize: 13,
                                    fontWeight: 600,
                                    marginBottom: 2,
                                }}
                            >
                                Коментар оператору
                            </div>
                            <div
                                className="muted"
                                style={{ fontSize: 12, marginBottom: 8 }}
                            >
                                {commentTarget.email}
                            </div>
                            <div
                                className="muted"
                                style={{ fontSize: 12, marginBottom: 6 }}
                            >
                                Ваш фідбек щодо продуктивності:
                            </div>
                        </div>
                        <form onSubmit={handleSubmit}>
                            <div style={{ marginBottom: 10 }}>
                                <textarea
                                    rows={4}
                                    value={commentText}
                                    onChange={(e) =>
                                        setCommentText(e.target.value)
                                    }
                                    placeholder="Наприклад: гарний прогрес за останній тиждень, продовжуй у тому ж темпі 💪"
                                    style={{
                                        width: '100%',
                                        resize: 'vertical',
                                        padding: '10px 12px',
                                        borderRadius: 12,
                                        border:
                                            '1px solid rgba(120,120,255,0.7)',
                                        outline: 'none',
                                        fontSize: 13,
                                        background: 'var(--bg)',
                                        color: 'var(--fg)',
                                        boxShadow:
                                            '0 0 0 1px rgba(255,255,255,0.04)',
                                    }}
                                />
                            </div>
                            {error && (
                                <div
                                    className="muted"
                                    style={{
                                        color: '#ff8080',
                                        fontSize: 12,
                                        marginBottom: 8,
                                    }}
                                >
                                    {error}
                                </div>
                            )}
                            <div
                                style={{
                                    display: 'flex',
                                    justifyContent: 'flex-end',
                                    gap: 8,
                                }}
                            >
                                <button
                                    type="button"
                                    className="btn sm"
                                    onClick={closeModal}
                                    disabled={sending}
                                >
                                    Скасувати
                                </button>
                                <button
                                    type="submit"
                                    className="btn sm primary"
                                    disabled={sending}
                                >
                                    {sending ? 'Надсилається…' : 'Надіслати'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    )
}
