import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // State
  // Initialize token from localStorage to maintain session on reload
  const token = ref(localStorage.getItem('token') || null)

  // Initialize user info from localStorage if available
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // Initialize isSuperAdmin from localStorage
  const isSuperAdmin = ref(localStorage.getItem('isSuperAdmin') === 'true')

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  // Actions
  /**
   * Set authentication data after successful login
   * @param {string} newToken - The JWT access token
   * @param {boolean} [superAdmin] - Whether the user is a super admin
   * @param {Object} [userInfo] - Optional user information
   */
  function setAuth(newToken, superAdmin = false, userInfo = null) {
    token.value = newToken
    localStorage.setItem('token', newToken)

    isSuperAdmin.value = superAdmin
    localStorage.setItem('isSuperAdmin', String(superAdmin))

    if (userInfo) {
      user.value = userInfo
      localStorage.setItem('user', JSON.stringify(userInfo))
    }
  }

  /**
   * Clear authentication data effectively logging the user out
   */
  function clearAuth() {
    token.value = null
    user.value = null
    isSuperAdmin.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('isSuperAdmin')
  }

  return {
    token,
    user,
    isSuperAdmin,
    isAuthenticated,
    setAuth,
    clearAuth
  }
})
