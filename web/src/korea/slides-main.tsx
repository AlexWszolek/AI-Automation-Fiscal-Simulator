import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import KoreaSlides from './KoreaSlides'
import '../styles/app.css'
import './korea.css'
import './slides.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KoreaSlides />
  </StrictMode>,
)
