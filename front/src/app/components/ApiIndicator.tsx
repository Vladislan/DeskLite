import React from 'react'
type S = 'ok'|'down'|'checking'
export default function ApiIndicator({status}:{status:S}){
    const title = status==='ok'?'API працює':status==='down'?'API недоступний':'Перевірка API'
    return <div className={`api-indicator ${status}`} title={title} aria-label={title} />
}
