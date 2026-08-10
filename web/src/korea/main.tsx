import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import KoreaApp from './KoreaApp'
import '../styles/app.css'
import './korea.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KoreaApp />
  </StrictMode>,
)
