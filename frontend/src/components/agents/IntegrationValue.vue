<template>
  <div class="integration-value">
    <div>
      <span>{{ label }}</span
      ><code>{{ value }}</code>
    </div>
    <q-btn flat round dense icon="content_copy" :aria-label="`Copy ${label}`" @click="copy" />
  </div>
</template>

<script setup lang="ts">
import { copyToClipboard } from 'quasar';

const props = defineProps<{ label: string; value: string }>();
async function copy() {
  await copyToClipboard(props.value);
}
</script>
