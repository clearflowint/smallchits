<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'

const { api } = useApi()
const router = useRouter()

const step = ref(1)

const step1 = ref({ chitti_name: '', rule_template: 'Incremental Model V1' })
const step2 = ref({ total_members: null, total_months: null, monthly_commission: null, undrawn_due: null, drawn_due: null })
const step3 = ref({ start_month_year: '', cycle_anchor_day: '' })
const step4 = ref({ members: [] })

const anchorDays = ['1st', '5th', '10th', '15th', '20th', '25th']
const submitting = ref(false)
const error = ref('')

const step1Valid = computed(() => step1.value.chitti_name.trim().length > 0)
const step2Valid = computed(() => {
  const s = step2.value
  return [s.total_members, s.total_months, s.monthly_commission, s.undrawn_due, s.drawn_due]
    .every((v) => v !== null && v !== '' && Number(v) > 0)
})
const step3Valid = computed(() => step3.value.start_month_year && step3.value.cycle_anchor_day)
const step4Valid = computed(
  () => step4.value.members.length === Number(step2.value.total_members) &&
        step4.value.members.every((m) => m.member_name && m.share_id && /^\+91\d{10}$/.test(m.phone_number))
)

function initRoster() {
  const n = Number(step2.value.total_members) || 0
  step4.value.members = Array.from({ length: n }, (_, i) => ({
    member_name: '',
    share_id: `SHARE${i + 1}`,
    phone_number: '+91'
  }))
}

function nextStep() {
  if (step.value === 2) initRoster()
  step.value++
}

async function submitOnboarding() {
  submitting.value = true
  error.value = ''
  try {
    await api.post('/onboarding/chitti', {
      step1: step1.value,
      step2: {
        total_members: Number(step2.value.total_members),
        total_months: Number(step2.value.total_months),
        monthly_commission: Number(step2.value.monthly_commission),
        undrawn_due: Number(step2.value.undrawn_due),
        drawn_due: Number(step2.value.drawn_due)
      },
      step3: step3.value,
      step4: step4.value
    })
    router.push('/home')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Something went wrong. Please check your inputs.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="px-4 py-4">
    <!-- Progress -->
    <div class="flex gap-1 mb-6">
      <div v-for="n in 4" :key="n" class="flex-1 h-1.5 rounded-full" :class="n <= step ? 'bg-clearflow-blue' : 'bg-white/10'"></div>
    </div>

    <!-- Step 1: Group Identity -->
    <div v-if="step === 1" class="space-y-4">
      <h2 class="text-xl font-bold">Group Identity</h2>
      <input v-model="step1.chitti_name" placeholder="Chitti Group Name" class="input-field" />
      <select v-model="step1.rule_template" class="input-field">
        <option>Incremental Model V1</option>
      </select>
      <button class="btn-primary w-full" :disabled="!step1Valid" @click="step++">Continue</button>
    </div>

    <!-- Step 2: Financial Parameters -->
    <div v-if="step === 2" class="space-y-4">
      <h2 class="text-xl font-bold">Financial Parameters</h2>
      <label class="block text-sm text-white/60">Total Members (S) <span class="text-red-400">*</span></label>
      <input v-model="step2.total_members" type="number" min="1" class="input-field" />
      <label class="block text-sm text-white/60">Total Months (M) <span class="text-red-400">*</span></label>
      <input v-model="step2.total_months" type="number" min="1" class="input-field" />
      <label class="block text-sm text-white/60">Monthly Commission (C) <span class="text-red-400">*</span></label>
      <input v-model="step2.monthly_commission" type="number" min="0" class="input-field" />
      <label class="block text-sm text-white/60">Undrawn Due <span class="text-red-400">*</span></label>
      <input v-model="step2.undrawn_due" type="number" min="0" class="input-field" />
      <label class="block text-sm text-white/60">Drawn Due <span class="text-red-400">*</span></label>
      <input v-model="step2.drawn_due" type="number" min="0" class="input-field" />
      <button class="btn-primary w-full" :disabled="!step2Valid" @click="nextStep">Continue</button>
    </div>

    <!-- Step 3: Cycle Calendar Anchor -->
    <div v-if="step === 3" class="space-y-4">
      <h2 class="text-xl font-bold">Cycle Calendar Anchor</h2>
      <input v-model="step3.start_month_year" type="month" class="input-field" />
      <label class="block text-sm text-white/60">Fixed Cycle Anchor Day (no custom dates)</label>
      <select v-model="step3.cycle_anchor_day" class="input-field">
        <option value="" disabled>Select anchor day</option>
        <option v-for="d in anchorDays" :key="d" :value="d">{{ d }} to {{ d }}</option>
      </select>
      <button class="btn-primary w-full" :disabled="!step3Valid" @click="step++">Continue</button>
    </div>

    <!-- Step 4: Member Roster -->
    <div v-if="step === 4" class="space-y-4">
      <h2 class="text-xl font-bold">Member Roster ({{ step4.members.length }})</h2>
      <div v-for="(m, i) in step4.members" :key="i" class="card space-y-2">
        <p class="text-xs text-white/40">Share #{{ i + 1 }}</p>
        <input v-model="m.member_name" placeholder="Member Name" class="input-field" />
        <input v-model="m.share_id" placeholder="Custom Share ID (e.g. CHAND1)" class="input-field" />
        <input v-model="m.phone_number" placeholder="+91XXXXXXXXXX" class="input-field" />
      </div>
      <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>
      <button class="btn-primary w-full" :disabled="!step4Valid || submitting" @click="submitOnboarding">
        {{ submitting ? 'Creating…' : 'Create Chitti Group' }}
      </button>
    </div>
  </div>
</template>
