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

    <section class="workspace-panel retrieval-options">
      <div class="option-row">
        <q-input
          v-model.number="limit"
          type="number"
          min="1"
          max="25"
          label="Results"
          outlined
          dense
        />
        <q-input
          v-model.number="candidateLimit"
          type="number"
          min="1"
          max="100"
          label="Candidates"
          outlined
          dense
        />
        <q-toggle v-model="rerank" label="Rerank" color="primary" />
        <q-toggle v-model="diversity" label="Diversity" color="primary" />
      </div>
      <q-expansion-item icon="tune" label="Retrieval tuning" dense>
        <div class="slider-grid">
          <div>
            <div class="slider-label">Lexical weight {{ lexicalWeight.toFixed(2) }}</div>
            <q-slider v-model="lexicalWeight" :min="0" :max="1" :step="0.05" label />
          </div>
          <div>
            <div class="slider-label">Diversity lambda {{ diversityLambda.toFixed(2) }}</div>
            <q-slider
              v-model="diversityLambda"
              :min="0"
              :max="1"
              :step="0.05"
              label
              :disable="!diversity"
            />
          </div>
          <div>
            <div class="slider-label">Minimum score {{ minScore.toFixed(2) }}</div>
            <q-slider v-model="minScore" :min="0" :max="1" :step="0.05" label />
          </div>
        </div>
      </q-expansion-item>
    </section>

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
            <q-item-label caption> Document {{ result.document_id }} </q-item-label>
            <div class="score-row">
              <q-chip dense square color="primary" text-color="white">
                final {{ result.score.toFixed(3) }}
              </q-chip>
              <q-chip v-if="typeof result.vector_score === 'number'" dense square>
                vector {{ result.vector_score.toFixed(3) }}
              </q-chip>
              <q-chip v-if="typeof result.lexical_score === 'number'" dense square>
                lexical {{ result.lexical_score.toFixed(3) }}
              </q-chip>
            </div>
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

import type { SearchOptions, SearchResult } from '@/services/api';
import type { GroupOption } from '@/types/workspace';

const props = defineProps<{
  groupOptions: GroupOption[];
  selectedGroupId: string | null;
  results: SearchResult[];
  busy: boolean;
}>();

const emit = defineEmits<{
  selectGroup: [groupId: string];
  search: [query: string, options: SearchOptions];
}>();

const query = ref('');
const limit = ref(8);
const candidateLimit = ref(30);
const rerank = ref(true);
const lexicalWeight = ref(0.35);
const diversity = ref(false);
const diversityLambda = ref(0.75);
const minScore = ref(0);
const currentGroupId = computed({
  get: () => props.selectedGroupId,
  set: (value) => {
    if (value) emit('selectGroup', value);
  },
});

function submitSearch() {
  if (!query.value.trim()) return;
  emit('search', query.value, {
    limit: limit.value,
    candidate_limit: candidateLimit.value,
    rerank: rerank.value,
    lexical_weight: lexicalWeight.value,
    diversity: diversity.value,
    diversity_lambda: diversityLambda.value,
    min_score: minScore.value > 0 ? minScore.value : null,
  });
}
</script>
