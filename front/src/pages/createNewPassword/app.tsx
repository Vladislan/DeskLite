import React, { useEffect, useMemo, useState } from 'react'
import { resetPassword } from '../../app/api/auth'

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
        <button
            className="btn sm white theme-fab"
            onClick={() => setTheme(next)}
            title="Змінити тему"
        >
            {theme === 'light' ? '🌙 Нічний' : '☀️ Денний'}
        </button>
    )
}

export default function CreateNewPasswordApp() {
    const [password1, setPassword1] = useState('')
    const [password2, setPassword2] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    const email = useMemo(() => {
        const params = new URLSearchParams(window.location.search)
        return (params.get('email') || '').trim()
    }, [])

    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const submit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        setSuccess(false)

        if (!email) {
            setError('Посилання некоректне: відсутній email')
            return
        }
        if (!password1 || !password2) {
            setError('Заповніть обидва поля паролю')
            return
        }
        if (password1 !== password2) {
            setError('Паролі не співпадають')
            return
        }
        if (password1.length < 8) {
            setError('Пароль має містити щонайменше 8 символів')
            return
        }

        setLoading(true)
        try {
            await resetPassword(email, password1)
            setSuccess(true)
        } catch (err: any) {
            const detail = err?.response?.data?.detail
            setError(detail || err?.message || 'Network Error')
        } finally {
            setLoading(false)
        }
    }

    const disableSubmit = loading || !password1 || !password2

    return (
        <div className="center-wrap">
            <ThemeSwitchFab />
            <button
                className="btn sm white"
                style={{ position: 'absolute', left: '1rem', top: '1rem' }}
                onClick={() => { window.location.href = '/login.html' }}
            >
                ← Назад до входу
            </button>

            <div className="auth-stack">
                <img src="/DeskLite_white.png" alt="DeskLite" className="auth-logo brand-dark" />
                <img src="/DeskLite_black.png" alt="DeskLite" className="auth-logo brand-light" />

                <form className="auth-card" onSubmit={submit} noValidate>
                    <h2>Новий пароль</h2>
                    <p className="muted small">
                        Встановіть новий пароль для акаунта:
                        {' '}
                        <strong>{email || '—'}</strong>
                    </p>

                    <div className="auth-field">
                        <input
                            className="auth-input"
                            placeholder="Новий пароль"
                            type="password"
                            value={password1}
                            onChange={(e) => setPassword1(e.target.value)}
                            autoComplete="new-password"
                        />
                    </div>
                    <div className="auth-field">
                        <input
                            className="auth-input"
                            placeholder="Підтвердіть новий пароль"
                            type="password"
                            value={password2}
                            onChange={(e) => setPassword2(e.target.value)}
                            autoComplete="new-password"
                        />
                    </div>

                    {error && (
                        <div className="muted small" style={{ color: '#fca5a5', paddingLeft: '5%' }}>
                            {error}
                        </div>
                    )}
                    {success && (
                        <div className="muted small" style={{ color: '#bbf7d0', paddingLeft: '5%' }}>
                            Пароль успішно змінено. Тепер ви можете увійти з новим паролем.
                        </div>
                    )}

                    <button className="auth-btn" disabled={disableSubmit}>
                        {loading ? 'Збереження…' : 'Зберегти новий пароль'}
                    </button>
                </form>
            </div>
        </div>
    )
}
