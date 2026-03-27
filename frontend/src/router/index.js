import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { requiresGuest: true }
  },
  // Authenticated routes wrapped in BaseLayout
  {
    path: '/',
    component: () => import('../components/layout/BaseLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/ChatView.vue'),
      },
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/DashboardView.vue'),
      },
      {
        path: 'kb/:id',
        name: 'KbDetail',
        component: () => import('../views/KbDetailView.vue'),
      },
      {
        path: 'profile',
        name: 'UserProfile',
        component: () => import('../views/UserProfileView.vue'),
      },
      {
        path: 'document/:id',
        name: 'DocumentDetail',
        component: () => import('../views/DocumentDetailView.vue'),
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('../views/SearchView.vue'),
      },
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('../views/SystemSettingsView.vue'),
        meta: { requiresSuperAdmin: true },
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Phase 2: Navigation Guards
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  const isAuthRequired = to.matched.some(record => record.meta.requiresAuth)

  const isGuestOnly = to.matched.some(record => record.meta.requiresGuest)
  const requiresSuperAdmin = to.matched.some(record => record.meta.requiresSuperAdmin)

  if (isAuthRequired && !authStore.isAuthenticated) {
    next({ name: 'Login' })
  } else if (requiresSuperAdmin && !authStore.isSuperAdmin) {
    ElMessage.error('Super-admin privileges required')
    next({ name: 'Dashboard' })
  } else if (isGuestOnly && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
