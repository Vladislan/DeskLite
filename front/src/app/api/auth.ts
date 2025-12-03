import { api } from './client'

const KEY_TOKEN = 'token'
const KEY_USER  = 'user'

export type UserRole = 'user' | 'operator' | 'admin'

export interface AuthUser {
    id: number
    email: string
    role: UserRole
    name?: string | null
    is_active?: boolean | null
}

export const getToken = () => localStorage.getItem(KEY_TOKEN)

export const setToken = (t: string | null) =>
    t ? localStorage.setItem(KEY_TOKEN, t) : localStorage.removeItem(KEY_TOKEN)

export const getCurrentUser = (): AuthUser | null => {
    const raw = localStorage.getItem(KEY_USER)
    if (!raw) return null
    try {
        return JSON.parse(raw) as AuthUser
    } catch {
        return null
    }
}

export const setCurrentUser = (u: AuthUser | null) =>
    u ? localStorage.setItem(KEY_USER, JSON.stringify(u)) : localStorage.removeItem(KEY_USER)

export const logout = () => { setToken(null); setCurrentUser(null) }

type LoginResp = { access_token?: string; token?: string; user?: AuthUser; detail?: string }

// ✅ перевірка, чи існує email
export async function checkEmail(email: string): Promise<boolean> {
    const r = await api.get<{ exists: boolean }>('/auth/check_email', { params: { email } })
    return !!r.data?.exists
}

// ✅ логін з підтримкою rememberMe
//    username, password – як було;
//    rememberMe – опційний, за замовчуванням true (щоб не ламати старі виклики).
export async function login(
    username: string,
    password: string,
    rememberMe: boolean = true
): Promise<{ token: string; user: AuthUser }> {
    const r = await api.post<LoginResp>('/auth/login', {
        username,
        password,
        remember_me: rememberMe,
    })
    const tok = r.data.access_token || r.data.token
    const usr = r.data.user
    if (!tok || !usr) {
        throw new Error(r.data.detail || 'Не вдалося увійти')
    }
    setToken(tok)
    setCurrentUser(usr)
    return { token: tok, user: usr }
}

// 🔹 Запит на відновлення паролю (створює "заявку на відновлення")
export async function requestPasswordRecovery(email: string): Promise<void> {
    await api.post('/auth/password-recovery-request', { email })
}

// 🔹 Встановлення нового паролю (форма createNewPassword.html)
export async function resetPassword(email: string, password: string): Promise<void> {
    await api.post('/auth/reset-password', { email, password })
}

export function pathByRole(role: UserRole): string {
    if (role === 'admin') return '/admin.html'
    if (role === 'operator') return '/operator.html'
    return '/user.html'
}

export function requireRole(allowed: UserRole[]) {
    const u = getCurrentUser()
    const t = getToken()
    if (!u || !t) {
        window.location.href = '/login.html'
        return null
    }
    if (!allowed.includes(u.role)) {
        window.location.href = pathByRole(u.role)
        return null
    }
    return u
}
