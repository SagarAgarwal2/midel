import axios from 'axios'

const api = axios.create({
  // Use same-origin requests in dev so Vite proxy handles backend routing.
  baseURL: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 30000,
})

export async function fetchApiData() {
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/data`)
  if (!response.ok) {
    throw new Error(`Failed to fetch /api/data: ${response.status}`)
  }
  return response.json()
}

export default api
