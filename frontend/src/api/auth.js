import http from './http'

/**
 * Register a new user
 * @param {Object} data - The registration payload
 * @param {string} data.username - User's username
 * @param {string} data.password - User's password
 * @param {string} [data.kb_id] - Optional Knowledge Base ID
 * @returns {Promise<Object>} The registered user data
 */
export const register = (data) => {
  return http.post('/auth/register', data)
}

/**
 * Login a user
 * @param {Object} data - The login payload
 * @param {string} data.username - User's username
 * @param {string} data.password - User's password
 * @returns {Promise<Object>} The login response containing access_token
 */
export const login = (data) => {
  return http.post('/auth/login', data)
}
