<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import ShareCard from '../components/ShareCard.vue'
import PaymentDrawer from '../components/PaymentDrawer.vue'
import DrawControl from '../components/DrawControl.vue'

const { api } = useApi()

const chittis = ref([])
const activeChitti = ref(null)
const shares = ref([])
const transactions = ref({}) // keyed by Share_ID
const loading = ref(true)

const activeTab = ref(0) // 5 sub-tabs, 4-5 shares each
const showScreenshotModal = ref(false)

const paymentDrawerOpen = ref(false)
const drawControlOpen = ref(false)
const selectedShare = ref(null)

const tabs = computed(() => {
  const chunks = []
  const perTab = Math.ceil(shares.value.length / 5) || 1
  for (let i = 0; i < shares.value.length; i += perTab) {
    chunks.push(shares.value.slice(i, i + perTab))
  }
  return chunks.length ? chunks : [[]]
})

async function loadChittis() {
  const res = await api.get('/chittis')
  chittis.value = res.data.chittis
  if (chittis.value.length) {
    activeChitti.value = chittis.value[0]
    await loadShares()
  }
  loading.value = false
}

async function loadShares() {
  if (!activeChitti.value) return
  const res = await api.get(`/shares/by-chitti/${activeChitti.value.Chitti_ID}`)
  shares.value = res.data.shares
}

function openPaymentDrawer(share) {
  selectedShare.value = share
  paymentDrawerOpen.value = true
}

function openDrawControl(share) {
  selectedShare.value = share
  drawControlOpen.value = true
}

async function onPaid() {
  await loadShares()
}
async function onDrawUpdated() {
  await loadShares()
}

async function spawnMonth() {
  if (!activeChitti.value) return
  try {
    await api.post(`/chittis/${activeChitti.value.Chitti_ID}/spawn-month`)
    await loadShares()
  } catch (e) {
    // 409 = already spawned this month, safe to ignore in UI
  }
}

onMounted(loadChittis)
</script>

<template>
  <div v-if="loading" class="p-6 text-center text-white/50">Loading…</div>

  <div v-else-if="!activeChitti" class="p-6 text-center">
    <p class="text-white/60 mb-4">No Chitti groups yet.</p>
    <router-link to="/onboarding" class="btn-primary inline-block">➕ Create your first Chitti</router-link>
  </div>

  <div v-else class="px-4 py-4 space-y-4">
    <!-- Top Block: Month Stats -->
    <div class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-bold text-lg">{{ activeChitti.Chitti_Name }}</h2>
        <span class="text-xs bg-clearflow-blue/20 text-clearflow-blue-light px-2 py-1 rounded-full">
          Month {{ activeChitti.Current_Active_Month }} / {{ activeChitti.Total_Months }}
        </span>
      </div>
      <div class="flex gap-2 mt-3">
        <button class="btn-primary flex-1 bg-white/10 text-sm" @click="spawnMonth">↻ Spawn Month</button>
        <button class="btn-primary flex-1 text-sm" @click="showScreenshotModal = true">📸 View Summary</button>
      </div>
    </div>

    <!-- Sub-tabs -->
    <div class="flex gap-1 overflow-x-auto pb-1 -mx-1 px-1">
      <button
        v-for="(tab, i) in tabs"
        :key="i"
        class="px-3 py-1.5 rounded-full text-sm shrink-0"
        :class="activeTab === i ? 'bg-clearflow-blue text-white' : 'bg-white/10 text-white/60'"
        @click="activeTab = i"
      >
        Group {{ i + 1 }}
      </button>
    </div>

    <!-- Bottom Block: Active Share Cards -->
    <div class="space-y-2">
      <ShareCard
        v-for="share in tabs[activeTab]"
        :key="share.Share_ID"
        :share="share"
        :transaction="transactions[share.Share_ID]"
        @open-drawer="openPaymentDrawer"
        @open-draw-control="openDrawControl"
      />
    </div>
  </div>

  <!-- Screenshot Summary Modal -->
  <Transition name="fade">
    <div v-if="showScreenshotModal" class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" @click="showScreenshotModal = false">
      <div class="card w-full max-w-sm" @click.stop>
        <h3 class="font-bold text-lg mb-3">{{ activeChitti.Chitti_Name }} — Month {{ activeChitti.Current_Active_Month }}</h3>
        <p class="text-sm text-white/70">Share this screenshot in your WhatsApp group.</p>
        <button class="btn-primary w-full mt-4" @click="showScreenshotModal = false">Close</button>
      </div>
    </div>
  </Transition>

  <PaymentDrawer
    :open="paymentDrawerOpen"
    :share="selectedShare"
    :transaction="selectedShare ? transactions[selectedShare.Share_ID] : null"
    :month-number="activeChitti?.Current_Active_Month || 1"
    @close="paymentDrawerOpen = false"
    @paid="onPaid"
  />
  <DrawControl
    :open="drawControlOpen"
    :share="selectedShare"
    :current-month="activeChitti?.Current_Active_Month || 1"
    @close="drawControlOpen = false"
    @updated="onDrawUpdated"
  />
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
