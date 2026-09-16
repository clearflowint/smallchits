<script setup>
import { useAuth } from '../composables/useAuth'
const { loginWithGoogle } = useAuth()
</script>

<template>
  <div class="min-h-[80vh] flex flex-col items-center justify-center px-6 text-center gap-6">
    <div class="w-16 h-16 rounded-2xl bg-clearflow-blue flex items-center justify-center text-3xl font-bold">⚙</div>
    <div>
      <h1 class="text-2xl font-bold">ClearFlow Small Chits</h1>
      <p class="text-white/60 mt-2">Digitize your Chitti group. Zero bookkeeping errors.</p>
    </div>
    <button @click="loginWithGoogle" class="btn-primary w-full flex items-center justify-center gap-2">
      <span>Sign in with Google</span>
    </button>
    <p class="text-xs text-white/40">Your Google email becomes your permanent manager account.</p>
  </div>
</template>
