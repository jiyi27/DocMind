import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { getAuthToken } from '@/utils/auth/storage'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120000,
})

function isAuthExpiredMessage(message) {
  if (!message) return false

  const normalizedMessage = String(message).toLowerCase()
  return normalizedMessage.includes('token has expired')
    || normalizedMessage.includes('invalid token')
    || normalizedMessage.includes('session expired')
}

async function redirectToLogin(message = 'Session expired, please login again') {
  const authStore = useAuthStore()
  authStore.clearAuth()
  ElMessage.error(message)

  if (router.currentRoute.value.name !== 'Login') {
    await router.replace({
      name: 'Login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  }
}

// Request Interceptor: Inject JWT Token
http.interceptors.request.use(
  (config) => {
    const token = getAuthToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response Interceptor: Handle DocMind Global Envelope and Errors
http.interceptors.response.use(
  (response) => {
    const res = response.data

    // DocMind Success Envelope
    if (res.code === 0) {
      return res.data
    }

    // DocMind Handled Business Error Envelope
    if (res.code === -1) {
      if (isAuthExpiredMessage(res.message)) {
        return redirectToLogin(res.message).then(() => Promise.reject(new Error(res.message || 'Unauthorized')))
      }

      ElMessage.error(res.message || 'Business Error')
      return Promise.reject(new Error(res.message || 'Error'))
    }

    // Pass through if not standard envelope (e.g. direct files/binary)
    return res
  },
  (error) => {
    // Handle specific HTTP Status Codes (e.g., 401 Unauthorized)
    if (error.response) {
      if (error.response.status === 401) {
        const detail = error.response.data?.detail || 'Session expired, please login again'
        return redirectToLogin(detail).then(() => Promise.reject(error))
      } else {
        const detail = error.response.data?.detail || error.message
        ElMessage.error(`Request Failed: ${detail}`)
      }
    } else {
      ElMessage.error(error.message || 'Network Error')
    }

    return Promise.reject(error)
  }
)

export default http
