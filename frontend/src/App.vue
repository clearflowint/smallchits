<script setup>
import { ref } from 'vue'
import { RouterView, RouterLink } from 'vue-router'
import { useAuth } from './composables/useAuth'

const drawerOpen = ref(false)
const { logout } = useAuth()
</script>

<template>
  <div class="min-h-screen flex flex-col max-w-md mx-auto relative">
    <!-- Top bar -->
    <header class="flex items-center justify-between px-4 py-3 border-b border-white/10 sticky top-0 bg-clearflow-slate/95 backdrop-blur z-20">
      <button @click="drawerOpen = true" class="text-2xl leading-none p-2 -ml-2" aria-label="Menu">☰</button>
      <span class="font-semibold tracking-tight">ClearFlow Chits</span>
      <div class="w-8"></div>
    </header>

    <!-- Page content -->
    <main class="flex-1 pb-20">
      <RouterView />
    </main>

    <!-- Sidebar Drawer -->
    <Transition name="fade">
      <div v-if="drawerOpen" class="fixed inset-0 bg-black/60 z-30" @click="drawerOpen = false">
        <aside
          class="absolute left-0 top-0 h-full w-72 bg-clearflow-slate border-r border-white/10 flex flex-col p-4"
          @click.stop
        >
          <button @click="drawerOpen = false" class="self-end text-xl p-2" aria-label="Close">✕</button>

          <nav class="flex-1 flex flex-col gap-1 mt-4">
            <RouterLink to="/home" class="px-3 py-3 rounded-xl hover:bg-white/10" @click="drawerOpen = false">🏠 Home</RouterLink>
            <RouterLink to="/summary" class="px-3 py-3 rounded-xl hover:bg-white/10" @click="drawerOpen = false">📊 Summary & Hub</RouterLink>
            <RouterLink to="/onboarding" class="px-3 py-3 rounded-xl hover:bg-white/10" @click="drawerOpen = false">➕ New Chitti</RouterLink>
            <button @click="logout" class="text-left px-3 py-3 rounded-xl hover:bg-white/10 text-red-400">⏻ Logout</button>
          </nav>

          <!-- Mandatory ClearFlow branding footer (Blueprint section 7 / 10) -->
          <div class="border-t border-white/10 pt-4 mt-4 flex items-center gap-2 opacity-70">
            <div class="w-6 h-6 rounded bg-clearflow-blue flex items-center justify-center text-xs font-bold">⚙</div>
            <span class="text-xs tracking-wide">POWERED BY CLEARFLOW AUTOMATIONS</span>
          </div>
        </aside>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
