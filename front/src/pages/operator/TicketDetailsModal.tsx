import React, { useMemo, useState } from 'react'
import { approveTicket, sendToAdmin } from '../../app/api/client'

type RoleKind = 'operator' | 'admin'

interface Props {
    ticket: any
    role?: RoleKind
    onClose: () => void
    reload: () => void
}

export default function TicketDetailsModal({ ticket, role = 'operator', onClose, reload }: Props) {
    const [answer, setAnswer] = useState('')
    const [stamping, setStamping] = useState<null | 'operator' | 'admin'>(null)

    const stampSrc = useMemo(() => {
        return stamping === 'admin'
            ? '/img/DeskLite_Admin_stamp_v2.png'
            : '/img/DeskLite_Operator_stamp_v2.png'
    }, [stamping])

    const prettyDept = (d?: string) => {
        switch (d) {
            case 'dev': return 'Відділ розробки'
            case 'impl': return 'Відділ впровадження'
            case 'info': return 'Інформаційний відділ'
            case 'mgmt': return 'Управління'
            default: return d ?? ''
        }
    }

    const approve = async () => {
        setStamping(role === 'admin' ? 'admin' : 'operator')
        try {
            await approveTicket(Number(ticket.id))
        } finally {
            setTimeout(() => { reload(); onClose() }, 850)
        }
    }

    const sendAdmin = async () => {
        await sendToAdmin(Number(ticket.id))
        reload()
        onClose()
    }

    return (
        <div className="modal">
            <div className="modal__backdrop" onClick={onClose} />
            <div className="modal__card">
                <div className="modal__head">
                    <div className="modal__title">Заявка #{ticket.id}</div>
                    <button className="btn sm ghost" onClick={onClose}>Закрити</button>
                </div>

                <div className="details-grid">
                    <div className="field">
                        <div className="field__label">Назва</div>
                        <div className="field__value">{ticket.title}</div>
                    </div>

                    <div className="field">
                        <div className="field__label">Відділ</div>
                        <div className="field__value">{prettyDept(ticket.dept) || '—'}</div>
                    </div>

                    <div className="field">
                        <div className="field__label">Тема</div>
                        <div className="field__value">{ticket.topic ?? '—'}</div>
                    </div>

                    <div className="field">
                        <div className="field__label">Посада</div>
                        <div className="field__value">{ticket.position ?? '—'}</div>
                    </div>

                    <div className="field">
                        <div className="field__label">Телефон</div>
                        <div className="field__value">{ticket.phone ?? '—'}</div>
                    </div>

                    {/* Робоча пошта + місце для штампа */}
                    <div className="field" style={{ position: 'relative' }}>
                        <div className="field__label">Робоча пошта</div>
                        <div className="field__value">{ticket.work_email ?? '—'}</div>

                        {stamping && (
                            <img src={stampSrc} alt="" className="stamp-anim" aria-hidden />
                        )}
                    </div>

                    <div className="field">
                        <div className="field__label">Резервна пошта</div>
                        <div className="field__value">{ticket.backup_email ?? '—'}</div>
                    </div>

                    <div className="field field--full">
                        <div className="field__label">Опис</div>
                        <div className="field__value pre-wrap">{ticket.description || '—'}</div>
                    </div>
                </div>

                <textarea
                    className="input"
                    rows={3}
                    placeholder="Коментар / відповідь..."
                    value={answer}
                    onChange={e => setAnswer(e.target.value)}
                    style={{ marginTop: 12 }}
                />

                <div className="actions" style={{ marginTop: 12 }}>
                    <button className="btn success" onClick={approve}>Погодити</button>

                    {/* для адміна – ховаємо кнопку “На погодження адміністратору” */}
                    {role !== 'admin' && (
                        <button className="btn blue" onClick={sendAdmin}>На погодження адміністратору</button>
                    )}

                    <button className="btn ghost" onClick={onClose}>Закрити</button>
                </div>
            </div>
        </div>
    )
}
