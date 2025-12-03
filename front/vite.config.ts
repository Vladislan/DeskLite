import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
    plugins: [react()],
    root: '.',
    build: {
        rollupOptions: {
            input: {
                login:    resolve(__dirname, 'login.html'),
                user:     resolve(__dirname, 'user.html'),
                operator: resolve(__dirname, 'operator.html'),
                admin:    resolve(__dirname, 'admin.html'),
            },
        },
    },
})
