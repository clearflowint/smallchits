import { ref } from 'vue'
import { useApi } from './useApi'

const isAuthenticated = ref(false)

export function useAuth() {
  const { api } = useApi()

  function loginWithGoogle() {
    // Full page redirect into the Day 1 Google OAuth flow
    window.location.href = '/api/auth/google/login'
  }

  async function logout() {
    await api.post('/auth/logout')
    isAuthenticated.value = false
    window.location.href = '/'
  }

  return { isAuthenticated, loginWithGoogle, logout }
}
