// src/pages/recovery/main.tsx
import React from 'react'
import { createRoot } from 'react-dom/client'
import RecoveryApp from './app'

// гарантовано тягнемо глобальні стилі (бекграунд GIF, токени теми тощо)
import '../../app/styles/global.css'

const rootEl = document.getElementById('root')
if (!rootEl) {
    throw new Error('recovery-password.html: <div id="root"></div> не знайдено')
}
createRoot(rootEl).render(<RecoveryApp />)
