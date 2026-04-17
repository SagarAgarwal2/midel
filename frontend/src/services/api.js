import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/'

const api = axios.create({
  // Use same-origin requests in dev so Vite proxy handles backend routing.
  baseURL: apiBaseUrl,
  timeout: 30000,
})

export async function fetchApiData() {
  const normalizedBase = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
  const response = await fetch(`${normalizedBase}/api/data`)
  if (!response.ok) {
    throw new Error(`Failed to fetch /api/data: ${response.status}`)
  }
  return response.json()
}

export default api
