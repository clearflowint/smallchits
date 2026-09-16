<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'

const { api } = useApi()

const chittis = ref([])
const activeChittiId = ref(null)
const summary = ref(null)
const shares = ref([])
const loading = ref(true)

const selectedShareIds = ref([])
const editingShare = ref(null)

async function loadAll() {
  const res = await api.get('/chittis')
  chittis.value = res.data.chittis
  if (chittis.value.length) {
    activeChittiId.value = chittis.value[0].Chitti_ID
    await loadSummary()
    await loadShares()
  }
  loading.value = false
}

async function loadSummary() {
  if (!activeChittiId.value) return
  const res = await api.get(`/dashboard/${activeChittiId.value}/summary`)
  summary.value = res.data
}

async function loadShares() {
  if (!activeChittiId.value) return
  const res = await api.get(`/shares/by-chitti/${activeChittiId.value}`)
  shares.value = res.data.shares
}

async function broadcast(target, messageType) {
  await api.post('/whatsapp/broadcast', {
    chitti_id: activeChittiId.value,
    target,
    message_type: messageType,
    share_ids: target === 'selected' ? selectedShareIds.value : null
  })
  alert('Messages sent.')
}

function toggleSelect(shareId) {
  const i = selectedShareIds.value.indexOf(shareId)
  if (i === -1) selectedShareIds.value.push(shareId)
  else selectedShareIds.value.splice(i, 1)
}

function openEditor(share) {
  editingShare.value = { ...share }
}

async function saveContact() {
  if (!editingShare.value) return
  await api.patch('/shares/contact', {
    share_id: editingShare.value.Share_ID,
    member_name: editingShare.value.Member_Name,
    phone_number: editingShare.value.Phone_Number
  })
  editingShare.value = null
  await loadShares()
}

onMounted(loadAll)
</script>

<template>
  <div v-if="loading" class="p-6 text-center text-white/50">Loading…</div>

  <div v-else-if="!summary" class="p-6 text-center text-white/50">No Chitti groups yet.</div>

  <div v-else class="px-4 py-4 space-y-5">
    <!-- Overall Financial Ledger Cards -->
    <div class="grid grid-cols-2 gap-3">
      <div class="card">
        <p class="text-xs text-white/40">Total Pending Dues</p>
        <p class="text-xl font-bold">₹{{ summary.total_pending_dues }}</p>
      </div>
      <div class="card">
        <p class="text-xs text-white/40">Advance Credit Reserve</p>
        <p class="text-xl font-bold">₹{{ summary.advance_credit_reserve }}</p>
      </div>
      <div class="card col-span-2">
        <p class="text-xs text-white/40">Earned Manager Commission</p>
        <p class="text-xl font-bold">₹{{ summary.earned_manager_commission }}</p>
      </div>
    </div>

    <!-- Pocket Cash Indicator -->
    <div
      class="card border-2"
      :class="summary.pocket_cash.color === 'green' ? 'border-clearflow-surplus' : 'border-clearflow-deficit'"
    >
      <p class="text-xs text-white/40 mb-1">Pocket Cash</p>
      <p
        class="text-2xl font-bold"
        :class="summary.pocket_cash.color === 'green' ? 'text-clearflow-surplus' : 'text-clearflow-deficit'"
      >
        {{ summary.pocket_cash.status === 'surplus' ? '🟢 SURPLUS' : '🔴 DEFICIT' }}
      </p>
      <p class="text-sm text-white/60 mt-1">
        Without advances: ₹{{ summary.pocket_cash.without_advances }} · With advances: ₹{{ summary.pocket_cash.with_advances }}
      </p>
    </div>

    <!-- WhatsApp Hub -->
    <div class="card space-y-3">
      <h3 class="font-bold">📲 WhatsApp Hub</h3>
      <div class="grid grid-cols-2 gap-2">
        <button class="btn-primary text-sm bg-white/10" @click="broadcast('all_pending', 'overdue')">
          Send to ALL Pending
        </button>
        <button class="btn-primary text-sm bg-white/10" @click="broadcast('all_shares', 'pre_due')">
          Send to ALL Shares
        </button>
        <button class="btn-primary text-sm col-span-2" @click="broadcast('all_shares', 'statement')">
          Send Personal Statements
        </button>
      </div>
    </div>

    <!-- Contact Editor -->
    <div class="card space-y-2">
      <h3 class="font-bold mb-2">✏️ Contact Editor</h3>
      <div v-for="s in shares" :key="s.Share_ID" class="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
        <div class="min-w-0">
          <p class="text-sm truncate">{{ s.Member_Name }}</p>
          <p class="text-xs text-white/40">{{ s.Phone_Number }}</p>
        </div>
        <button class="text-xs text-clearflow-blue underline shrink-0" @click="openEditor(s)">Edit</button>
      </div>
    </div>
  </div>

  <!-- Edit modal -->
  <Transition name="fade">
    <div v-if="editingShare" class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" @click="editingShare = null">
      <div class="card w-full max-w-sm" @click.stop>
        <h3 class="font-bold mb-3">Edit {{ editingShare.Share_ID }}</h3>
        <input v-model="editingShare.Member_Name" class="input-field mb-2" placeholder="Member Name" />
        <input v-model="editingShare.Phone_Number" class="input-field mb-3" placeholder="+91XXXXXXXXXX" />
        <button class="btn-primary w-full" @click="saveContact">💾 Save</button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
