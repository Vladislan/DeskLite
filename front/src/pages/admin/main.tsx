import React from 'react'
import { createRoot } from 'react-dom/client'

// ВАЖЛИВО: імпортуємо готовий компонент
import AdminApp from './App'

// Глобальні стилі
import '../../app/styles/global.css'

createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <AdminApp />
    </React.StrictMode>
)
