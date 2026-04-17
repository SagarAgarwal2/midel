import axios from 'axios'

// Base URL from environment
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
})

export default api