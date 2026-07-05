import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import App from './App.vue'
import './styles/main.css'

createApp(App).use(createPinia()).use(ElementPlus).mount('#app')
