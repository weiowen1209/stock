import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import App from './App.vue'
import './styles/main.css'

window.addEventListener('error', (event) => {
  console.error('[runtime error]', event.error ?? event.message)
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('[unhandled rejection]', event.reason)
})

createApp(App).use(createPinia()).use(ElementPlus).mount('#app')
