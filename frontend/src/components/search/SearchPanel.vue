<template>
  <div class="screen-stack">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">Search Bench</div>
        <h1>Test document search</h1>
        <p>Use this screen to check whether indexed documents return useful search results.</p>
      </div>
      <q-select
        v-model="currentGroupId"
        :options="groupOptions"
        emit-value
        map-options
        label="Document group"
        outlined
        dense
        class="hero-select"
      />
    </section>

    <q-banner v-if="!selectedGroupId" rounded class="feedback-banner feedback-banner-error">
      <template #avatar>
        <q-icon name="folder_off" />
      </template>
      Select a document group before running a search.
    </q-banner>

    <q-form class="search-command-bar" @submit.prevent="submitSearch">
      <q-input v-model="query" label="Ask a question" outlined dense class="search-input">
        <template #prepend>
          <q-icon name="manage_search" />
        </template>
      </q-input>
      <q-btn
        type="submit"
        color="primary"
        icon="search"
        label="Search"
        :loading="busy"
        :disable="!selectedGroupId"
        no-caps
      />
    </q-form>

    <section class="workspace-panel results-panel">
      <div class="panel-heading">
        <div>
          <h2>Results</h2>
          <p>{{ results.length }} source chunks found</p>
        </div>
        <q-icon name="format_quote" />
      </div>

      <q-list v-if="results.length" separator class="result-list">
        <q-item v-for="result in results" :key="result.chunk_id" class="result-item">
          <q-item-section>
            <q-item-label class="result-text">{{ result.text }}</q-item-label>
            <q-item-label caption>
              Document {{ result.document_id }} - score {{ result.score.toFixed(3) }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else class="empty-state">
        <q-icon name="search_off" />
        <span>Ask a question after documents finish processing.</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

import type { SearchResult } from '@/services/api';
import type { GroupOption } from '@/types/workspace';

const props = defineProps<{
  groupOptions: GroupOption[];
  selectedGroupId: string | null;
  results: SearchResult[];
  busy: boolean;
}>();

const emit = defineEmits<{
  selectGroup: [groupId: string];
  search: [query: string];
}>();

const query = ref('');
const currentGroupId = computed({
  get: () => props.selectedGroupId,
  set: (value) => {
    if (value) emit('selectGroup', value);
  },
});

function submitSearch() {
  if (!query.value.trim()) return;
  emit('search', query.value);
}
</script>
