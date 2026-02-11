import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Capacitor } from '@capacitor/core'
import App from './App'
import './index.css'

try {
  const isNative = Capacitor?.isNativePlatform?.() || import.meta.env.MODE === 'android'
  const isElectron = typeof window !== "undefined" && Boolean(window?.electronAPI)
  document.documentElement.classList.toggle('apk', Boolean(isNative || isElectron))
} catch {
  // ignore
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
