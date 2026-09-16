import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true // sends the httpOnly session cookie set by /api/auth/google/callback
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Authentication Guardrail: bounce back to Google Sign-In
      window.location.href = '/api/auth/google/login'
    }
    return Promise.reject(err)
  }
)

export function useApi() {
  return { api }
}
