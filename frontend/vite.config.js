import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'   // <-- NUEVO

export default defineConfig({
  plugins: [react(), tailwindcss()],          // <-- MODIFICADO (antes: [react()])
  server: { port: 5173, strictPort: true },   // <-- NUEVO
})