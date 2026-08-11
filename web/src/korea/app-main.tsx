import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import KoreaScenarioApp from './KoreaScenarioApp'
import '../styles/app.css'
import './korea.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KoreaScenarioApp />
  </StrictMode>,
)
