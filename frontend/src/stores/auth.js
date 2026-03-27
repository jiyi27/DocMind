import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  clearStoredAuthState,
  getStoredAuthState,
  setAuthToken,
  setStoredIsSuperAdmin,
  setStoredKbId,
  setStoredRole,
  setStoredUser,
} from '@/utils/auth/storage'

export const useAuthStore = defineStore('auth', () => {
  const storedAuthState = getStoredAuthState()

  // State
  // Initialize token from persisted auth storage to maintain session on reload
  const token = ref(storedAuthState.token)

  // Initialize user info from persisted auth storage if available
  const user = ref(storedAuthState.user)

  // Initialize isSuperAdmin from persisted auth storage
  const isSuperAdmin = ref(storedAuthState.isSuperAdmin)

  // Initialize kbId from persisted auth storage (stored as string, always compare via String())
  const kbId = ref(storedAuthState.kbId)

  // Initialize role from persisted auth storage ('admin' | 'user' | null)
  const role = ref(storedAuthState.role)

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
    setAuthToken(newToken)

    isSuperAdmin.value = superAdmin
    setStoredIsSuperAdmin(superAdmin)

    if (userKbId != null) {
      kbId.value = String(userKbId)
      setStoredKbId(userKbId)
    }

    if (userRole) {
      role.value = userRole
      setStoredRole(userRole)
    }

    if (userInfo) {
      user.value = userInfo
      setStoredUser(userInfo)
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
    clearStoredAuthState()
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
