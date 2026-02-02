import { createRouter, createWebHistory } from 'vue-router'
import ApplicationPage from '../views/ApplicationPage.vue'
import CallPage from '../views/CallPage.vue'
import AnalysisPage from '../views/AnalysisPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/application', name: 'application', component: ApplicationPage },
    { path: '/call', name: 'call', component: CallPage },
    { path: '/analysis', name: 'analysis', component: AnalysisPage },
    { path: '/', redirect: '/application' },
  ],
})
