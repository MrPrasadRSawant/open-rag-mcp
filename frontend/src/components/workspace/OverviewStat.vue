<template>
  <div class="stat-tile" :class="`stat-tile-${tone}`">
    <q-icon :name="icon" size="22px" />
    <div>
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
      <div v-if="caption" class="stat-caption">{{ caption }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { StatTone } from '@/types/workspace';

withDefaults(
  defineProps<{
    label: string;
    value: string | number;
    icon: string;
    caption?: string;
    tone?: StatTone;
  }>(),
  {
    caption: '',
    tone: 'slate',
  },
);
</script>
