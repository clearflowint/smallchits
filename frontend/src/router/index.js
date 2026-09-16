import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  { path: '/onboarding', name: 'Onboarding', component: () => import('../views/OnboardingView.vue') },
  { path: '/home', name: 'Home', component: () => import('../views/HomeView.vue') }, // Page 1
  { path: '/summary', name: 'Summary', component: () => import('../views/SummaryView.vue') } // Page 2
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
