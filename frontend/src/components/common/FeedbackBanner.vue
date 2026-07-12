<template>
  <q-banner v-if="message" rounded class="feedback-banner" :class="toneClass">
    <template #avatar>
      <q-icon :name="tone === 'error' ? 'error' : 'check_circle'" />
    </template>
    {{ message }}
    <template #action>
      <q-btn flat dense icon="close" aria-label="Dismiss" @click="$emit('dismiss')" />
    </template>
  </q-banner>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  message: string;
  tone: 'error' | 'success';
}>();

defineEmits<{
  dismiss: [];
}>();

const toneClass = computed(() =>
  props.tone === 'error' ? 'feedback-banner-error' : 'feedback-banner-success',
);
</script>
