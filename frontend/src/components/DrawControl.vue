<script setup>
import { ref, watch } from 'vue'
import { useApi } from '../composables/useApi'

const props = defineProps({
  open: { type: Boolean, default: false },
  share: { type: Object, default: null },
  currentMonth: { type: Number, default: 1 }
})
const emit = defineEmits(['close', 'updated'])

const { api } = useApi()
const status = ref('Undrawn')
const monthDrawn = ref(1)
const saving = ref(false)

watch(() => props.share, (s) => {
  if (s) {
    status.value = s.Draw_Status || 'Undrawn'
    monthDrawn.value = s.Month_Drawn || props.currentMonth
  }
})

async function save() {
  if (!props.share) return
  saving.value = true
  try {
    const res = await api.post('/shares/draw', {
      share_id: props.share.Share_ID,
      draw_status: status.value,
      month_drawn: status.value === 'Drawn' ? Number(monthDrawn.value) : null
    })
    emit('updated', res.data)
    emit('close')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Transition name="slide">
    <div v-if="open" class="fixed inset-0 z-40 flex items-end">
      <div class="absolute inset-0 bg-black/60" @click="emit('close')"></div>
      <div class="relative w-full max-w-md mx-auto bg-clearflow-slate rounded-t-3xl p-5 pb-8 border-t border-white/10">
        <div class="w-10 h-1 bg-white/20 rounded-full mx-auto mb-4"></div>
        <h3 class="font-bold text-lg mb-1">Draw Status — {{ share?.Member_Name }}</h3>
        <p class="text-xs text-white/40 mb-4">No separate reversal screen — just toggle and save.</p>

        <label class="block text-sm text-white/60 mb-1">Status</label>
        <select v-model="status" class="input-field mb-3">
          <option value="Undrawn">Undrawn</option>
          <option value="Drawn">Drawn 🏆</option>
        </select>

        <template v-if="status === 'Drawn'">
          <label class="block text-sm text-white/60 mb-1">Month Drawn</label>
          <input v-model="monthDrawn" type="number" min="1" :max="currentMonth" class="input-field mb-3" />
        </template>

        <button class="btn-primary w-full" :disabled="saving" @click="save">
          {{ saving ? 'Saving…' : '💾 Save' }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(20px); }
</style>
