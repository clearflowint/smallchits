<script setup>
defineProps({
  share: { type: Object, required: true },
  transaction: { type: Object, default: null }
})
const emit = defineEmits(['open-drawer', 'open-draw-control'])

function statusColor(status) {
  if (status === 'Verified') return 'bg-clearflow-surplus/20 text-clearflow-surplus'
  if (status === 'Partial') return 'bg-clearflow-pending/20 text-clearflow-pending'
  return 'bg-clearflow-deficit/20 text-clearflow-deficit'
}
</script>

<template>
  <div class="card flex items-center justify-between gap-3" @click="emit('open-drawer', share)">
    <div class="min-w-0">
      <p class="font-semibold truncate">{{ share.Member_Name }}</p>
      <p class="text-xs text-white/40 truncate">{{ share.Share_ID }} · {{ share.Draw_Status }}</p>
    </div>
    <div class="flex flex-col items-end gap-1 shrink-0">
      <span
        v-if="transaction"
        class="text-xs px-2 py-1 rounded-full font-medium"
        :class="statusColor(transaction.Payment_Status)"
      >
        {{ transaction.Payment_Status }}
      </span>
      <span v-if="transaction" class="text-xs text-white/50">₹{{ transaction.Pending_Dues }} due</span>
      <button
        class="text-xs text-clearflow-blue underline"
        @click.stop="emit('open-draw-control', share)"
      >
        Draw status
      </button>
    </div>
  </div>
</template>
