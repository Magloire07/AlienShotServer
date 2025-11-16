import { createRouter, createWebHistory } from 'vue-router'
import AdminView from '../views/AdminView.vue'
import ShareView from '../views/ShareView.vue'

const routes = [
  { path: '/', redirect: '/admin' },
  { path: '/admin', name: 'admin', component: AdminView },
  { path: '/share/:token', name: 'share', component: ShareView, props: true },
  { path: '/:pathMatch(.*)*', redirect: '/admin' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
