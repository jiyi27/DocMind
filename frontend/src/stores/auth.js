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

  // Initialize kbId from localStorage (stored as string, always compare via String())
  const kbId = ref(localStorage.getItem('kbId') || null)

  // Initialize role from localStorage ('admin' | 'user' | null)
  const role = ref(localStorage.getItem('role') || null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  /**
   * Whether the current user is the admin of a specific knowledge base.
   * A KB admin has role === 'admin' and is bound to that KB.
   * @param {string|number} targetKbId
   */
  function isKbAdmin(targetKbId) {
    return role.value === 'admin' && String(kbId.value) === String(targetKbId)
  }

  /**
   * Whether the current user can manage (delete / modify) a specific knowledge base.
   * True for super admins and for the KB's own admin.
   * @param {string|number} targetKbId
   */
  function canManageKb(targetKbId) {
    return isSuperAdmin.value || isKbAdmin(targetKbId)
  }

  /**
   * Whether the current user can access (view) a specific knowledge base.
   * Super admins can access all; regular users can only access their own KB.
   * @param {string|number} targetKbId
   */
  function canAccessKb(targetKbId) {
    return isSuperAdmin.value || String(kbId.value) === String(targetKbId)
  }

  // Actions
  /**
   * Set authentication data after successful login.
   * @param {string} newToken - The JWT access token
   * @param {boolean} [superAdmin] - Whether the user is a super admin
   * @param {Object} [userInfo] - Optional user information
   * @param {string|number} [userKbId] - The KB this user belongs to
   * @param {string} [userRole] - The user's role ('admin' | 'user')
   */
  function setAuth(newToken, superAdmin = false, userInfo = null, userKbId = null, userRole = null) {
    token.value = newToken
    localStorage.setItem('token', newToken)

    isSuperAdmin.value = superAdmin
    localStorage.setItem('isSuperAdmin', String(superAdmin))

    if (userKbId != null) {
      kbId.value = String(userKbId)
      localStorage.setItem('kbId', String(userKbId))
    }

    if (userRole) {
      role.value = userRole
      localStorage.setItem('role', userRole)
    }

    if (userInfo) {
      user.value = userInfo
      localStorage.setItem('user', JSON.stringify(userInfo))
    }
  }

  /**
   * Clear authentication data effectively logging the user out.
   */
  function clearAuth() {
    token.value = null
    user.value = null
    isSuperAdmin.value = false
    kbId.value = null
    role.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('isSuperAdmin')
    localStorage.removeItem('kbId')
    localStorage.removeItem('role')
  }

  return {
    token,
    user,
    isSuperAdmin,
    kbId,
    role,
    isAuthenticated,
    isKbAdmin,
    canManageKb,
    canAccessKb,
    setAuth,
    clearAuth,
  }
})
