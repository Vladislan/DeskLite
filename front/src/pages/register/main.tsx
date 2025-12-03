import React from 'react'
import { createRoot } from 'react-dom/client'
import RegisterApp from './app'
import '../../app/styles/global.css'

const root = document.getElementById('root')
if (!root) throw new Error('register.html: #root не знайдено')

createRoot(root).render(<RegisterApp />)
