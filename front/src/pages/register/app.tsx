import React, { useEffect, useState } from 'react'
import { api } from '../../app/api/client'
import { setToken, setCurrentUser, pathByRole, AuthUser } from '../../app/api/auth'

type Tab = 'user' | 'operator'

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

export default function RegisterApp(){
    const [tab, setTab] = useState<Tab>('user')

    // Спільні поля
    const [email, setEmail] = useState('')
    const [phone, setPhone] = useState('')
    const [fullName, setFullName] = useState('')

    // Паролі
    const [password, setPassword] = useState('')          // для користувача
    const [opPassword, setOpPassword] = useState('')      // для оператора

    // Лише для користувача
    const [position, setPosition] = useState('')

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [done, setDone] = useState(false)
    const [doneMsg, setDoneMsg] = useState<string>('')

    useEffect(() => {
        const saved = (localStorage.getItem('theme') as 'light'|'dark') || 'dark'
        document.documentElement.setAttribute('data-theme', saved)
    }, [])

    const submit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null); setLoading(true)

        try {
            if (tab === 'user') {
                // Явна реєстрація користувача: одразу токен
                const r = await api.post('/auth/register', {
                    email,
                    password,
                    phone,
                    full_name: fullName,
                    position,
                })
                const tok: string = r.data?.access_token || r.data?.token
                const usr: AuthUser = r.data?.user
                if (!tok || !usr) throw new Error('Помилка реєстрації (немає токена або користувача)')
                setToken(tok)
                setCurrentUser(usr)
                window.location.href = pathByRole(usr.role)
                return
            } else {
                // Заявка оператора: відправляємо і бажаний пароль окремим полем
                // (бек може його поки ігнорувати; додаємо для подальшого автоприйому)
                await api.post('/auth/register-operator', {
                    email,
                    phone,
                    full_name: fullName,
                    desired_password: opPassword,
                })
                setDoneMsg('Заявку на реєстрацію оператора надіслано адміністратору. Коли погодять — отримаєте лист із доступом.')
                setDone(true)
            }
        } catch (err: any) {
            setError(
                err?.response?.data?.detail ||
                (tab === 'user'
                    ? 'Не вдалося зареєструватися. Спробуйте пізніше або зверніться до адміністратора.'
                    : 'Не вдалося надіслати заявку оператора.')
            )
        } finally {
            setLoading(false)
        }
    }

    const disabled =
        loading ||
        !email ||
        !phone ||
        !fullName ||
        (tab === 'user' && (!position || !password)) ||
        (tab === 'operator' && !opPassword)

    return (
        <div className="center-wrap">
            <ThemeSwitchFab />
            <a className="btn sm white faq-fab" href="/login.html">← Назад до входу</a>

            <div className="auth-stack">
                <img src="/DeskLite_white.png" alt="DeskLite" className="auth-logo brand-dark" />
                <img src="/DeskLite_black.png" alt="DeskLite" className="auth-logo brand-light" />

                <form className="auth-card" onSubmit={submit}>
                    <h2>Реєстрація</h2>

                    {/* Таби */}
                    <div className="actions" style={{ margin: '8px 5%' }}>
                        <button type="button"
                                className={`btn sm ${tab === 'user' ? 'primary' : 'ghost'}`}
                                onClick={() => setTab('user')}>
                            Користувач
                        </button>
                        <button type="button"
                                className={`btn sm ${tab === 'operator' ? 'primary' : 'ghost'}`}
                                onClick={() => setTab('operator')}>
                            Оператор
                        </button>
                    </div>

                    {!done ? (
                        <>
                            <div className="auth-field">
                                <input
                                    className="auth-input"
                                    placeholder="Пошта"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    autoComplete="email"
                                    required
                                />
                            </div>

                            <div className="auth-field">
                                <input
                                    className="auth-input"
                                    placeholder="Номер телефону"
                                    value={phone}
                                    onChange={(e) => setPhone(e.target.value)}
                                    pattern="[\d\s()+\-]{6,}"
                                    title="Введіть номер телефону"
                                    autoComplete="tel"
                                    required
                                />
                            </div>

                            <div className="auth-field">
                                <input
                                    className="auth-input"
                                    placeholder="ПІБ"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    autoComplete="name"
                                    required
                                />
                            </div>

                            {tab === 'user' && (
                                <>
                                    <div className="auth-field">
                                        <input
                                            className="auth-input"
                                            placeholder="Спеціальність / Позиція"
                                            value={position}
                                            onChange={(e) => setPosition(e.target.value)}
                                            required
                                        />
                                    </div>
                                    <div className="auth-field">
                                        <input
                                            className="auth-input"
                                            placeholder="Пароль"
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            autoComplete="new-password"
                                            required
                                        />
                                    </div>
                                </>
                            )}

                            {tab === 'operator' && (
                                <div className="auth-field">
                                    <input
                                        className="auth-input"
                                        placeholder="Пароль для майбутнього входу"
                                        type="password"
                                        value={opPassword}
                                        onChange={(e) => setOpPassword(e.target.value)}
                                        autoComplete="new-password"
                                        required
                                    />
                                </div>
                            )}

                            {error && (
                                <div className="muted small" style={{ color: '#fca5a5', width:'90%', margin:'0 auto' }}>
                                    {error}
                                </div>
                            )}

                            <button className="auth-btn" disabled={disabled}>
                                {loading ? 'Надсилаємо…' : (tab === 'user' ? 'Зареєструватися' : 'Надіслати заявку')}
                            </button>

                            <div className="auth-aux" style={{ textAlign:'center' }}>
                                Уже маєте акаунт? <a className="auth-link" href="/login.html">Увійти</a>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="muted small" style={{width:'90%', margin:'0 auto 10px', textAlign:'center'}}>
                                {doneMsg}
                            </div>
                            <a className="auth-btn" href="/login.html">Перейти до входу</a>
                        </>
                    )}
                </form>
            </div>
        </div>
    )
}
