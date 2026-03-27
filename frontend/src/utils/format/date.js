export function formatDate(value, options = {}) {
  if (!value) return '-'

  return new Date(value).toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...options,
  })
}

export function formatDateTime(value, options = {}) {
  if (!value) return '-'

  return new Date(value).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  })
}
