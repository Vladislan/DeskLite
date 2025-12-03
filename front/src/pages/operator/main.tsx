
import { createRoot } from 'react-dom/client'
import OperatorApp from './App'
import '../../app/styles/global.css'
import React, { StrictMode } from 'react';

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <OperatorApp />
    </StrictMode>
);