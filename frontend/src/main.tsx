import 'vite/modulepreload-polyfill';
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('--react-documents')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
