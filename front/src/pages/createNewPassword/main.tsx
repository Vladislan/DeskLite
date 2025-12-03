import React from 'react'
import ReactDOM from 'react-dom/client'
import CreateNewPasswordApp from './app'

const rootEl = document.getElementById('root')
if (rootEl) {
    ReactDOM.createRoot(rootEl).render(
        <React.StrictMode>
            <CreateNewPasswordApp />
        </React.StrictMode>
    )
}
