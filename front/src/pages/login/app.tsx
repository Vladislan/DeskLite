// front/src/login/app.tsx
import React, { useEffect, useState } from 'react'
import { login, pathByRole, checkEmail } from '../../app/api/auth'

// === Тема (як було) ===
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

// === FAQ ===
type QA = { q: string; a: React.ReactNode }
function FaqModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    useEffect(() => {
        if (!open) return
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [open, onClose])
    if (!open) return null
    const items: QA[] = [
        { q: 'Що таке DeskLite і для чого він?', a: <>DeskLite — це легкий сервіс заявок…</> },
        { q: 'Як увійти?', a: <>Введіть e-mail і пароль, видані адміністратором…</> },
        { q: 'Забув пароль — що робити?', a: <>Скористайтесь «Забули пароль?»…</> },
    ]
    return (
        <div className="modal" role="dialog" aria-modal="true" aria-labelledby="faq-title">
            <div className="modal__backdrop" onClick={onClose} />
            <div className="modal__card">
                <div className="modal__head">
                    <div className="modal__title" id="faq-title">FAQ • Часті запитання</div>
                    <button className="btn ghost sm" onClick={onClose} aria-label="Закрити">✕</button>
                </div>
                <div className="faq-body">
                    {items.map((it, i) => (
                        <details key={i} className="faq-item" open={i < 1}>
                            <summary className="faq-q">{it.q}</summary>
                            <div className="faq-a">{it.a}</div>
                        </details>
                    ))}
                </div>
            </div>
        </div>
    )
}

// === Константи для повідомлень від бека ===
const EMAIL_NOT_FOUND = 'Данний email не є зареєстрованим'
const WRONG_PASSWORD = 'Невірний пароль'

// ключ для збереження вибору чекбоксу
const REMEMBER_KEY = 'desk_remember_me'

export default function LoginApp() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [faqOpen, setFaqOpen] = useState(false)

    // локальна помилка саме під e-mail
    const [emailError, setEmailError] = useState<string | null>(null)

    // чекбокс "Запам'ятати мене" — за замовчуванням УВІМКНЕНИЙ
    const [rememberMe, setRememberMe] = useState<boolean>(() => {
        const raw = localStorage.getItem(REMEMBER_KEY)
        if (raw === null) return true
        return raw === '1'
    })

    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const isEmailValid = (value: string) =>
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())

    const onEmailBlur = async () => {
        const email = username.trim()
        setEmailError(null)
        if (!email) return

        if (!isEmailValid(email)) {
            setEmailError('Вкажіть коректний email')
            return
        }

        try {
            const exists = await checkEmail(email)
            if (!exists) setEmailError(EMAIL_NOT_FOUND)
        } catch {
            // ігноруємо мережеві помилки на blur
        }
    }

    const submit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        setEmailError(null)

        const email = username.trim()
        if (!isEmailValid(email)) {
            setEmailError('Вкажіть коректний email')
            return
        }
        if (!password) {
            setError('Вкажіть пароль')
            return
        }

        setLoading(true)
        try {
            // 🔹 передаємо rememberMe в API
            const { user } = await login(email, password, rememberMe)

            // зберігаємо вибір чекбоксу локально
            localStorage.setItem(REMEMBER_KEY, rememberMe ? '1' : '0')

            window.location.href = pathByRole(user.role)
        } catch (err: any) {
            const status = err?.response?.status
            const detail = err?.response?.data?.detail

            if (status === 404 || detail === EMAIL_NOT_FOUND) {
                setEmailError(EMAIL_NOT_FOUND)
                setError(null)
            } else if (status === 401 || /парол/i.test(detail || '') || detail === WRONG_PASSWORD) {
                setError(WRONG_PASSWORD)
            } else {
                setError(detail || err?.message || 'Network Error')
            }
        } finally {
            setLoading(false)
        }
    }

    const disableSubmit = loading || !username || !password

    return (
        <div className="center-wrap">
            <ThemeSwitchFab />
            <button
                className="btn sm white faq-fab"
                onClick={() => setFaqOpen(true)}
                title="Часті запитання"
            >
                ❓ FAQ
            </button>

            <div className="auth-stack">
                <img src="/DeskLite_white.png" alt="DeskLite" className="auth-logo brand-dark" />
                <img src="/DeskLite_black.png" alt="DeskLite" className="auth-logo brand-light" />

                <form className="auth-card" onSubmit={submit} noValidate>
                    <h2>Увійти</h2>

                    <div className="auth-field">
                        <input
                            className={`auth-input ${emailError ? 'input-error' : ''}`}
                            placeholder="Email"
                            value={username}
                            onChange={(e) => {
                                setUsername(e.target.value)
                                if (emailError) setEmailError(null)
                            }}
                            onBlur={onEmailBlur}
                            autoComplete="username"
                            inputMode="email"
                        />
                        {emailError && <div className="field-error">{emailError}</div>}
                    </div>

                    <div className="auth-field">
                        <input
                            className="auth-input"
                            placeholder="Пароль"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoComplete="current-password"
                        />
                    </div>

                    {/* чекбокс "Запам'ятати мене" + пояснення */}
                    <div className="auth-extra" style={{ width: '90%', margin: '4px auto 0', fontSize: 12 }}>
                        <label className="auth-checkbox" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <input
                                type="checkbox"
                                checked={rememberMe}
                                onChange={(e) => setRememberMe(e.target.checked)}
                            />
                            <span>Запам’ятати мене на цьому пристрої</span>
                        </label>
                        <div className="muted small" style={{ marginTop: 4 }}>
                            {rememberMe
                                ? 'Сесія буде тривалішою (до ~30 днів, поки ви не вийдете з акаунта).'
                                : 'Сесія буде короткою — для спільних / тимчасових комп’ютерів.'}
                        </div>
                    </div>

                    {error && (
                        <div className="muted small" style={{ color: '#fca5a5', paddingLeft: '5%' }}>
                            {error}
                        </div>
                    )}

                    <button className="auth-btn" disabled={disableSubmit}>
                        {loading ? 'Вхід…' : 'Увійти'}
                    </button>

                    <div className="auth-aux" style={{ textAlign:'center' }}>
                        <a className="auth-link" href="/recovery-password.html">Забули пароль?</a>
                        <span className="muted small"> · </span>
                        <a className="auth-link" href="/register.html">Реєстрація</a>
                    </div>
                </form>
            </div>

            <div className="login-footer">
                <span className="login-footer__title">DeskLite</span>
                <span className="login-footer__text">
                    — внутрішній сервіс підтримки та заявок для вашої компанії.
                    Створюйте, відстежуйте та вирішуйте звернення в одному кабінеті.
                </span>
            </div>

            <FaqModal open={faqOpen} onClose={() => setFaqOpen(false)} />
        </div>
    )
}
