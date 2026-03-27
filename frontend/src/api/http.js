import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { getAuthToken } from '@/utils/auth/storage'
import { getErrorDetail, isAuthExpiredMessage, unwrapApiResponse } from '@/utils/http/errors'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120000,
})

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
    const result = unwrapApiResponse(response)

    if (result.ok) {
      return result.data
    }

    if (isAuthExpiredMessage(result.message)) {
      return redirectToLogin(result.message).then(() => Promise.reject(new Error(result.message || 'Unauthorized')))
    }

    ElMessage.error(result.message || 'Business Error')
    return Promise.reject(new Error(result.message || 'Error'))
  },
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        const detail = getErrorDetail(error) || 'Session expired, please login again'
        return redirectToLogin(detail).then(() => Promise.reject(error))
      }

      ElMessage.error(`Request Failed: ${getErrorDetail(error)}`)
    } else {
      ElMessage.error(getErrorDetail(error))
    }

    return Promise.reject(error)
  }
)

export default http
