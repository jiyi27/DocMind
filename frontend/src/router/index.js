import { createRouter, createWebHistory } from 'vue-router'
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

  // Determine if the route requires authentication. 
  // We use explicitly matched meta, and also fallback to checking if it's not a guest route.
  const isAuthRequired = to.matched.some(record => record.meta.requiresAuth) ||
    (!['Login', 'Register'].includes(to.name))

  const isGuestOnly = to.matched.some(record => record.meta.requiresGuest)

  if (isAuthRequired && !authStore.isAuthenticated) {
    // Redirect unauthenticated users to login page
    next({ name: 'Login' })
  } else if (isGuestOnly && authStore.isAuthenticated) {
    // Redirect authenticated users away from guest pages (login/register) to the dashboard
    next({ name: 'Dashboard' })
  } else {
    // Proceed as normal
    next()
  }
})

export default router
