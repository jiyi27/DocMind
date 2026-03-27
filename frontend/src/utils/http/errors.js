export function isAuthExpiredMessage(message) {
  if (!message) return false

  const normalizedMessage = String(message).toLowerCase()
  return normalizedMessage.includes('token has expired')
    || normalizedMessage.includes('invalid token')
    || normalizedMessage.includes('session expired')
}

export function getErrorDetail(error) {
  return error?.response?.data?.detail || error?.message || 'Network Error'
}

export function unwrapApiResponse(response) {
  const payload = response.data

  if (payload?.code === 0) {
    return {
      ok: true,
      data: payload.data,
      message: payload.message || '',
    }
  }

  if (payload?.code === -1) {
    return {
      ok: false,
      data: null,
      message: payload.message || 'Error',
    }
  }

  return {
    ok: true,
    data: payload,
    message: '',
  }
}
