import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client'
import UserApp from './App'
import '../../app/styles/global.css'
import OperatorApp from "../operator/App";

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <UserApp />
    </StrictMode>
);
