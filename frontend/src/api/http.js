import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

// Request Interceptor: Inject JWT Token
http.interceptors.request.use(
  (config) => {
    // We will retrieve the token from localStorage or Pinia here in Phase 2
    const token = localStorage.getItem('token')
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
        ElMessage.error('Session expired, please login again')
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
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
