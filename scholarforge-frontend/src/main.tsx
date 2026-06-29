import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Init dark mode
if (localStorage.getItem('scholarforge-theme')) {
  try {
    const state = JSON.parse(localStorage.getItem('scholarforge-theme')!).state;
    if (state.theme === 'dark') document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  } catch (e) {}
} else {
  // default to dark
  document.documentElement.classList.add('dark');
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
