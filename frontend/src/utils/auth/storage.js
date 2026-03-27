const STORAGE_KEYS = {
  token: 'token',
  user: 'user',
  isSuperAdmin: 'isSuperAdmin',
  kbId: 'kbId',
  role: 'role',
}

function readStorage(key) {
  return localStorage.getItem(key)
}

function writeStorage(key, value) {
  if (value == null || value === '') {
    localStorage.removeItem(key)
    return
  }

  localStorage.setItem(key, value)
}

function readJsonStorage(key) {
  const raw = readStorage(key)
  if (!raw) return null

  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem(key)
    return null
  }
}

export function getAuthToken() {
  return readStorage(STORAGE_KEYS.token)
}

export function setAuthToken(token) {
  writeStorage(STORAGE_KEYS.token, token)
}

export function getStoredUser() {
  return readJsonStorage(STORAGE_KEYS.user)
}

export function setStoredUser(user) {
  if (!user) {
    localStorage.removeItem(STORAGE_KEYS.user)
    return
  }

  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user))
}

export function getStoredIsSuperAdmin() {
  return readStorage(STORAGE_KEYS.isSuperAdmin) === 'true'
}

export function setStoredIsSuperAdmin(value) {
  writeStorage(STORAGE_KEYS.isSuperAdmin, String(Boolean(value)))
}

export function getStoredKbId() {
  return readStorage(STORAGE_KEYS.kbId)
}

export function setStoredKbId(kbId) {
  writeStorage(STORAGE_KEYS.kbId, kbId == null ? null : String(kbId))
}

export function getStoredRole() {
  return readStorage(STORAGE_KEYS.role)
}

export function setStoredRole(role) {
  writeStorage(STORAGE_KEYS.role, role)
}

export function getStoredAuthState() {
  return {
    token: getAuthToken(),
    user: getStoredUser(),
    isSuperAdmin: getStoredIsSuperAdmin(),
    kbId: getStoredKbId(),
    role: getStoredRole(),
  }
}

export function clearStoredAuthState() {
  localStorage.removeItem(STORAGE_KEYS.token)
  localStorage.removeItem(STORAGE_KEYS.user)
  localStorage.removeItem(STORAGE_KEYS.isSuperAdmin)
  localStorage.removeItem(STORAGE_KEYS.kbId)
  localStorage.removeItem(STORAGE_KEYS.role)
}
