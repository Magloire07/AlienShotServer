import axios from 'axios'

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
export const apiBaseUrl = rawBaseUrl.replace(/\/$/, '')

export const adminHeaders = (password) => ({
  'X-Admin-Password': password
})

export const photoFileUrl = (photoId, password) => {
  const params = new URLSearchParams({ password })
  return `${apiBaseUrl}/photos/${photoId}/file?${params}`
}

export const shareFileUrl = (token, photoId) => `${apiBaseUrl}/shares/${token}/files/${photoId}`

const api = axios.create({
  baseURL: apiBaseUrl
})

export default api
