import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import KoreaDash from './KoreaDash'
import '../styles/app.css'
import './korea.css'
import './dash.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KoreaDash />
  </StrictMode>,
)
