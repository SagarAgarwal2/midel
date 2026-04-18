import axios from 'axios'

const configuredBase =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'https://midel.onrender.com'

const normalizedBase = configuredBase.replace(/\/$/, '')

const api = axios.create({
  baseURL: normalizedBase,
  timeout: 30000,
})

export default api