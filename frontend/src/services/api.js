import axios from 'axios'

const api = axios.create({
  // Use same-origin requests in dev so Vite proxy handles backend routing.
  baseURL: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 30000,
})

export default api
