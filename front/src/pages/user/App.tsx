import React, { useCallback, useEffect, useRef, useState } from 'react'
import { requireRole, logout } from '../../app/api/auth'
import { createTask, listTasks, listQuestions, listAnswers, hardDeleteTicket } from '../../app/api/client'
import type { Task, Question } from '../../../types'
import UserQuestionsCard from './QuestionsCard'

type DeptKey = '' | 'dev' | 'impl' | 'info' | 'mgmt'
const TOPICS: Record<Exclude<DeptKey, ''>, string[]> = {
    dev:['Погодження щодо змін','Кадрові зміни','Пропозиції'],
    impl:['Погодження щодо подальшого впровадження','Кадрові зміни','Інфраструктурні зміни проекту'],
    info:['Погодження щодо розповсюдження','Кадрові зміни'],
    mgmt:['Внесення кадрових змін за проміжок часу','Розповсюдження щодо нововнесених змін умов праці'],
}

function useTheme(): ['light'|'dark',(t:'light'|'dark')=>void]{
    const initial = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
    const [theme,setTheme] = React.useState<'light'|'dark'>(initial)
    React.useEffect(()=>{ document.documentElement.setAttribute('data-theme', theme); localStorage.setItem('theme', theme) },[theme])
    return [theme,setTheme]
}
function ThemeSwitch(){
    const [theme,setTheme]=useTheme()
    const next = theme==='light'?'dark':'light'
    return <button className="btn sm white" onClick={()=>setTheme(next)} title="Змінити тему">{theme==='light'?'🌙 Нічний':'☀️ Денний'}</button>
}

export default function UserApp(){
    const me = requireRole(['user'])!

    // атрибут теми на першому рендері
    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const [items,setItems] = useState<Task[]>([])

    const [dept,setDept] = useState<DeptKey>('')
    const [topic,setTopic] = useState('')
    const [position,setPosition] = useState('')
    const [phone,setPhone] = useState('')
    const [workEmail,setWorkEmail] = useState('')
    const [backupEmail,setBackupEmail] = useState('')
    const [description,setDescription] = useState('')

    const [questions,setQuestions] = useState<Question[]>([])
    const [notifiedIds,setNotifiedIds] = useState<number[]>([])
    const [notification,setNotification] = useState<string|null>(null)

    const didInit = useRef(false)

    const loadTasks = useCallback(async ()=>{ const res=await listTasks(1,100); setItems(res.items) },[])
    const loadQuestions = useCallback(async ()=>{ const res=await listQuestions({ author_id: me.id }); setQuestions(res ?? []) },[me?.id])

    useEffect(()=>{ if(!me?.id || didInit.current) return; didInit.current=true; loadTasks(); loadQuestions() },[me?.id,loadTasks,loadQuestions])

    useEffect(()=>{
        async function checkAnswers(){
            for(const q of questions){
                if(q.status==='answered' && !notifiedIds.includes(q.id)){
                    const ans = await listAnswers(q.id)
                    if(ans.length>0){ setNotification(`Вам відповіли на питання: «${q.title}»`); setNotifiedIds(p=>[...p,q.id]); setTimeout(()=>setNotification(null),7000) }
                }
            }
        }
        if(questions.length>0) checkAnswers()
        const interval=setInterval(loadQuestions,15000)
        return ()=>clearInterval(interval)
    },[questions,loadQuestions,notifiedIds])

    if(!me) return null

    const isPhoneOk = /^\+380\d{9}$/.test(phone.trim())
    const isWorkOk = /@work\.ua$/i.test(workEmail.trim())
    const canSubmit = !!dept && !!topic && !!position.trim() && isPhoneOk && isWorkOk && !!description.trim()

    const submit = async ()=>{
        if(!canSubmit) return
        await createTask({
            title: `${topic} (${labelDept(dept)})`,
            description: description.trim(),
            dept, topic,
            position: position.trim(),
            phone: phone.trim(),
            work_email: workEmail.trim(),
            backup_email: backupEmail.trim() || undefined,
        })
        setDept(''); setTopic(''); setPosition(''); setPhone(''); setWorkEmail(''); setBackupEmail(''); setDescription('')
        await loadTasks()
    }

    const badge = (s: Task['status']) => {
        const cls = s==='done' ? 'badge green'
            : s==='in_progress' ? 'badge orange'
                : s==='canceled' ? 'badge danger'
                    : s==='blocked' ? 'badge warn'
                        : s==='triage' ? 'badge blue'
                            : 'badge gray'
        return <span className={cls}>{String(s)}</span>
    }

    const topicsForDept = (dept && TOPICS[dept as Exclude<DeptKey,''>]) || []
    useEffect(()=>{ setTopic('') },[dept])

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
                    <button className="btn sm white" onClick={()=>{ logout(); location.href='/login.html' }}>Вийти</button>
                </div>
            </header>

            <main className="container">
                {/* Створення заявки */}
                <section className="card">
                    <h3>Створити заявку</h3>

                    <div className="form-grid form-grid--2">
                        <select className="input" value={dept} onChange={(e)=>setDept(e.target.value as DeptKey)}>
                            <option value="">Оберіть відділ…</option>
                            <option value="dev">Відділ розробки</option>
                            <option value="impl">Відділ впровадження</option>
                            <option value="info">Інформаційний відділ</option>
                            <option value="mgmt">Управління</option>
                        </select>
                        <select className="input" value={topic} onChange={(e)=>setTopic(e.target.value)} disabled={!dept}>
                            <option value="">{dept ? 'Оберіть тему…' : 'Спочатку оберіть відділ'}</option>
                            {topicsForDept.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                    </div>

                    <div className="form-grid form-grid--2 section-gap">
                        <input className="input" placeholder="Посада" value={position} onChange={(e)=>setPosition(e.target.value)} />
                        <input className="input" placeholder="+380XXXXXXXXX" value={phone} onChange={(e)=>setPhone(e.target.value)} />
                    </div>

                    <div className="form-grid form-grid--2 section-gap">
                        <input className="input" placeholder="Робоча пошта (@work.ua)" value={workEmail} onChange={(e)=>setWorkEmail(e.target.value)} />
                        <input className="input" placeholder="Резервна пошта (будь-який домен)" value={backupEmail} onChange={(e)=>setBackupEmail(e.target.value)} />
                    </div>

                    <div className="section-gap">
            <textarea className="input textarea" placeholder="Опишіть вашу заявку…" rows={4}
                      value={description} onChange={(e)=>setDescription(e.target.value)} />
                    </div>

                    <div className="small" style={{ color:'var(--muted)', marginTop:6, marginBottom:8 }}>
                        {!isPhoneOk && phone && 'Телефон має бути у форматі +380XXXXXXXXX. '}
                        {!isWorkOk && workEmail && 'Робоча пошта має закінчуватись на @work.ua.'}
                    </div>

                    <div className="actions">
                        <button className="btn primary" disabled={!canSubmit} onClick={submit}>Створити</button>
                    </div>
                </section>

                {/* Мої заявки */}
                <section className="card">
                    <h3>Мої заявки</h3>
                    {items.length===0 ? (
                        <div className="muted">Порожньо</div>
                    ) : (
                        <div className="table-wrap">
                            <table className="table">
                                <thead>
                                <tr>
                                    <th style={{ width: 90 }}>ID</th>
                                    <th>Назва</th>
                                    <th style={{ width: 160 }}>Статус</th>
                                    <th style={{ width: 160 }}>Дії</th>
                                </tr>
                                </thead>
                                <tbody>
                                {items.map((t)=>(
                                    <tr key={String(t.id)}>
                                        <td>#{String(t.id)}</td>
                                        <td>
                                            {t.title}
                                            {('dept' in t || 'topic' in t) && (
                                                <div className="small" style={{ color:'var(--muted)' }}>
                                                    {('dept' in t) && labelDept((t as any).dept)}{('topic' in t) && ` • ${(t as any).topic}`}
                                                </div>
                                            )}
                                        </td>
                                        <td>{badge(t.status)}</td>
                                        <td>
                                            <div className="actions">
                                                {(t.status === 'new' || t.status === 'canceled') && (
                                                    <button
                                                        className="btn sm danger"
                                                        onClick={async ()=>{
                                                            if(!confirm(`Видалити вашу заявку #${t.id}?`)) return
                                                            await hardDeleteTicket(Number(t.id))
                                                            setItems(prev => prev.filter(x => String(x.id) !== String(t.id)))
                                                        }}
                                                    >Видалити</button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                <UserQuestionsCard />
            </main>

            {notification && (<div className="notif-popup">{notification}</div>)}
        </div>
    )
}

function labelDept(d:DeptKey){
    switch(d){
        case 'dev': return 'Відділ розробки'
        case 'impl': return 'Відділ впровадження'
        case 'info': return 'Інформаційний відділ'
        case 'mgmt': return 'Управління'
        default: return ''
    }
}
