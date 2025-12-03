// src/pages/recovery/app.tsx
import React, { useEffect, useState } from 'react'
import { api } from '../../app/api/client'

function useTheme(): ['light'|'dark',(t:'light'|'dark')=>void]{
    const initial = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
    const [theme, setTheme] = useState<'light'|'dark'>(initial)
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme)
        localStorage.setItem('theme', theme)
    }, [theme])
    return [theme, setTheme]
}
function ThemeSwitchFab(){
    const [theme, setTheme] = useTheme()
    const next = theme === 'light' ? 'dark' : 'light'
    return (
        <button className="btn sm white theme-fab" onClick={() => setTheme(next)} title="Змінити тему">
            {theme === 'light' ? '🌙 Нічний' : '☀️ Денний'}
        </button>
    )
}

export default function RecoveryApp(){
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [done, setDone] = useState(false)

    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const submit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null); setLoading(true)
        try {
            await api.post('/auth/password/recovery', { email }) // підлаштуй під бек
            setDone(true)
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Не вдалося надіслати посилання. Спробуйте ще раз або зверніться до адміністратора.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="center-wrap">
            <ThemeSwitchFab />

            {/* ліва верхня кнопка */}
            <a className="btn sm white faq-fab" href="/login.html">← Назад до входу</a>

            <div className="auth-stack">
                <img src="/DeskLite_white.png" alt="DeskLite" className="auth-logo brand-dark" />
                <img src="/DeskLite_black.png" alt="DeskLite" className="auth-logo brand-light" />

                <form className="auth-card" onSubmit={submit}>
                    <h2>Відновлення паролю</h2>

                    {!done ? (
                        <>
                            <div className="muted small" style={{width:'90%', margin:'0 auto 6px'}}>
                                Вкажіть e-mail, і ми надішлемо посилання для скидання паролю.
                            </div>
                            <div className="auth-field">
                                <input
                                    className="auth-input"
                                    placeholder="Ваш email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    type="email"
                                    autoComplete="email"
                                    required
                                />
                            </div>
                            {error && (
                                <div className="muted small" style={{ color: '#fca5a5', width:'90%', margin:'0 auto' }}>
                                    {error}
                                </div>
                            )}
                            <button className="auth-btn" disabled={loading || !email}>
                                {loading ? 'Надсилаємо…' : 'Надіслати посилання'}
                            </button>

                            <div className="auth-aux">
                                <a className="auth-link" href="/login.html">Пам’ятаєте пароль? Увійти</a>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="muted small" style={{width:'90%', margin:'0 auto 10px'}}>
                                Якщо в системі є обліковий запис <b>{email}</b>, посилання для відновлення вже відправлено.
                                Перевірте вхідні та «Спам». Лист дійсний обмежений час.
                            </div>
                            <a className="auth-btn" href="/login.html">Повернутися до входу</a>
                        </>
                    )}
                </form>
            </div>
        </div>
    )
}
