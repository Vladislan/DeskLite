import React, {useEffect, useState} from 'react'
import { listQuestions, listAnswers, type Question } from '../../app/api/client'

export default function QuestionsAdminCard(){
    const [items, setItems] = useState<Question[]>([])
    const [open, setOpen]   = useState<number|null>(null)
    const [ans, setAns]     = useState<Record<number,string>>({})

    useEffect(()=>{ (async()=>{
        const qs = await listQuestions({limit:200})
        setItems(qs)
    })() },[])

    const openQ = async (q:Question)=>{
        setOpen(q.id)
        const list = await listAnswers(q.id)
        setAns(s=>({...s, [q.id]: list.map(a=>`• ${a.created_at.slice(0,19).replace('T',' ')} — ${a.content}`).join('\n')}))
    }

    return (
        <section className="card">
            <h3>Питання користувачів</h3>
            <div className="table-wrap">
                <table className="table">
                    <thead><tr>
                        <th style={{width:90}}>ID</th><th>Автор</th><th>Заголовок</th><th>Статус</th><th style={{width:160}}>Дії</th>
                    </tr></thead>
                    <tbody>
                    {items.map(q=>(
                        <React.Fragment key={q.id}>
                            <tr>
                                <td>#{q.id}</td>
                                <td>#{q.author_id}</td>
                                <td>{q.title}</td>
                                <td><span className="badge gray">{q.status}</span></td>
                                <td><button className="btn sm" onClick={()=>openQ(q)}>Показати відповіді</button></td>
                            </tr>
                            {open===q.id && (
                                <tr><td colSpan={5}>
                                    <pre className="muted small" style={{whiteSpace:'pre-wrap'}}>{ans[q.id]||'—'}</pre>
                                </td></tr>
                            )}
                        </React.Fragment>
                    ))}
                    </tbody>
                </table>
            </div>
        </section>
    )
}
