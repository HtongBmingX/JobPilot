import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/agent': 'http://127.0.0.1:8000',
      '/upload': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/applications': 'http://127.0.0.1:8000',
      '/resumes': 'http://127.0.0.1:8000',
      '/profile': 'http://127.0.0.1:8000',
      '/status': 'http://127.0.0.1:8000',
    },
  },
})
