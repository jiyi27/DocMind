const DEFAULT_BRAND_NAME = 'DocMind'
const DEFAULT_FAVICON_PATH = '/favicon.svg'

function normalizeAssetPath(value, fallback = '') {
  if (typeof value !== 'string') {
    return fallback
  }

  const trimmed = value.trim()
  return trimmed || fallback
}

export const branding = {
  name: normalizeAssetPath(import.meta.env.VITE_BRAND_NAME, DEFAULT_BRAND_NAME),
  logoPath: normalizeAssetPath(import.meta.env.VITE_BRAND_LOGO_PATH),
  faviconPath: normalizeAssetPath(import.meta.env.VITE_BRAND_FAVICON_PATH, DEFAULT_FAVICON_PATH),
}

export function applyBranding() {
  document.title = branding.name

  let favicon = document.querySelector("link[rel='icon']")
  if (!favicon) {
    favicon = document.createElement('link')
    favicon.setAttribute('rel', 'icon')
    document.head.appendChild(favicon)
  }

  favicon.setAttribute('href', branding.faviconPath)
}
