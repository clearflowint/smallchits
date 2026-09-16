<script setup>
import { ref, computed, watch } from 'vue'
import { useApi } from '../composables/useApi'

const props = defineProps({
  open: { type: Boolean, default: false },
  share: { type: Object, default: null },
  transaction: { type: Object, default: null },
  monthNumber: { type: Number, default: 1 }
})
const emit = defineEmits(['close', 'paid'])

const { api } = useApi()
const amount = ref('')
const submitting = ref(false)
const warning = ref(null) // { type: 'partial' | 'overpay', amount }

watch(() => props.open, (v) => {
  if (v) { amount.value = ''; warning.value = null }
})

// RIGHT-THUMB GUARDRAIL: Confirm button disabled by default, activates only
// when digits are entered (Blueprint section 7).
const canConfirm = computed(() => amount.value !== '' && Number(amount.value) > 0)

function setPreset(v) {
  amount.value = String(v)
}

async function confirmPayment(force = false) {
  if (!canConfirm.value || !props.share || !props.transaction) return
  submitting.value = true
  try {
    const res = await api.post('/shares/payment', {
      share_id: props.share.Share_ID,
      month_number: props.monthNumber,
      amount_paid: Number(amount.value),
      force_partial_confirm: force
    })
    emit('paid', res.data)
    emit('close')
  } catch (e) {
    if (e.response?.status === 409) {
      warning.value = { type: 'partial', detail: e.response.data.detail }
    } else {
      warning.value = { type: 'error', detail: e.response?.data?.detail || 'Payment failed' }
    }
  } finally {
    submitting.value = false
  }
}

function handleConfirmClick() {
  const due = Number(props.transaction?.Amount_Due || 0)
  const paid = Number(amount.value)
  if (paid > due) {
    warning.value = { type: 'overpay', excess: (paid - due).toFixed(2) }
    // Overpayment still proceeds — server auto-routes excess to Advance Credit.
    confirmPayment(true)
    return
  }
  confirmPayment(false)
}
</script>

<template>
  <Transition name="slide">
    <div v-if="open" class="fixed inset-0 z-40 flex items-end">
      <div class="absolute inset-0 bg-black/60" @click="emit('close')"></div>
      <div class="relative w-full max-w-md mx-auto bg-clearflow-slate rounded-t-3xl p-5 pb-8 border-t border-white/10">
        <div class="w-10 h-1 bg-white/20 rounded-full mx-auto mb-4"></div>

        <h3 class="font-bold text-lg">{{ share?.Member_Name }}</h3>
        <p class="text-xs text-white/40 mb-4">{{ share?.Share_ID }} · Month {{ monthNumber }}</p>

        <p class="text-sm text-white/60 mb-2">
          Due: ₹{{ transaction?.Amount_Due }} · Already paid: ₹{{ transaction?.Amount_Paid || '0.00' }}
        </p>

        <div class="flex gap-2 mb-3">
          <button class="btn-primary flex-1 bg-white/10" @click="setPreset(transaction?.Amount_Due)">
            ₹{{ transaction?.Amount_Due }}
          </button>
          <button class="btn-primary flex-1 bg-white/10" @click="setPreset(Number(transaction?.Amount_Due) + 1000)">
            +₹1,000
          </button>
        </div>

        <input
          v-model="amount"
          type="number"
          inputmode="numeric"
          placeholder="Enter amount received"
          class="input-field mb-3"
        />

        <p v-if="warning?.type === 'partial'" class="text-clearflow-pending text-sm mb-3">
          ⚠ Amount is less than due — this will be marked <strong>Partial</strong>. Tap Confirm again to proceed.
        </p>
        <p v-if="warning?.type === 'overpay'" class="text-clearflow-blue-light text-sm mb-3">
          ℹ ₹{{ warning.excess }} extra will be moved to Advance Credit Reserve.
        </p>
        <p v-if="warning?.type === 'error'" class="text-clearflow-deficit text-sm mb-3">{{ warning.detail }}</p>

        <!-- Right-thumb guardrail: disabled until digits entered -->
        <button
          class="btn-primary w-full"
          :disabled="!canConfirm || submitting"
          @click="warning?.type === 'partial' ? confirmPayment(true) : handleConfirmClick()"
        >
          {{ submitting ? 'Confirming…' : 'Confirm Payment' }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(20px); }
</style>
