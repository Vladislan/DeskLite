// src/pages/login/main.tsx
import React from 'react'
import { createRoot } from 'react-dom/client'
import LoginApp from './app'   // <-- рівно 'app', якщо файл 'app.tsx'

const root = document.getElementById('root')!
createRoot(root).render(<LoginApp />)
