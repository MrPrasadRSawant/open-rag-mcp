<template>
  <div class="screen-stack">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">LLM Config</div>
        <h1>Configure models</h1>
        <p>Create immutable embedding and chat LLM configurations for your workspace.</p>
      </div>
      <q-btn
        color="primary"
        icon="add"
        label="Add provider key"
        no-caps
        @click="openCreateDialog"
      />
    </section>

    <section class="workspace-panel table-panel llm-config-panel">
      <div class="panel-heading table-heading">
        <div>
          <h2>Provider configs</h2>
          <p>{{ configs.length }} model configurations</p>
        </div>
        <q-icon name="encrypted" />
      </div>

      <q-table
        class="llm-config-table"
        flat
        :rows="configs"
        :columns="columns"
        :visible-columns="visibleColumns"
        :grid="$q.screen.lt.sm"
        row-key="id"
        :pagination="{ rowsPerPage: 8 }"
      >
        <template #item="props">
          <div class="llm-config-mobile-item">
            <div class="llm-config-mobile-head">
              <div>
                <div class="llm-config-mobile-name">{{ props.row.name }}</div>
                <div class="llm-config-mobile-model">
                  {{ props.row.embedding_model || props.row.chat_model || 'No model' }}
                </div>
              </div>
              <q-btn
                flat
                dense
                round
                color="negative"
                icon="delete"
                :disable="
                  busy || props.row.provider === 'internal' || props.row.in_use_by_groups > 0
                "
                @click="openDeleteDialog(props.row)"
              >
                <q-tooltip>Delete provider config</q-tooltip>
              </q-btn>
            </div>
            <div class="llm-config-mobile-meta">
              <q-chip dense square color="primary" text-color="white">
                {{ providerLabel(props.row.provider) }}
              </q-chip>
              <q-chip dense square>{{ typeLabel(props.row.purpose) }}</q-chip>
              <q-chip dense square :color="props.row.is_active ? 'positive' : 'grey'">
                {{ props.row.is_active ? 'Active' : 'Inactive' }}
              </q-chip>
            </div>
          </div>
        </template>
        <template #body-cell-provider="props">
          <q-td :props="props">
            <q-chip dense square color="primary" text-color="white">
              {{ providerLabel(props.row.provider) }}
            </q-chip>
          </q-td>
        </template>
        <template #body-cell-purpose="props">
          <q-td :props="props">
            <q-chip dense square>{{ typeLabel(props.row.purpose) }}</q-chip>
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-chip dense square :color="props.row.is_active ? 'positive' : 'grey'">
              {{ props.row.is_active ? 'Active' : 'Inactive' }}
            </q-chip>
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <div class="row-actions">
              <q-btn
                flat
                dense
                round
                color="negative"
                icon="delete"
                :disable="
                  busy || props.row.provider === 'internal' || props.row.in_use_by_groups > 0
                "
                @click="openDeleteDialog(props.row)"
              >
                <q-tooltip>
                  {{
                    props.row.provider === 'internal'
                      ? 'The internal Default config is always available'
                      : props.row.in_use_by_groups
                        ? `Used by ${props.row.in_use_by_groups} document group(s)`
                        : 'Delete provider config'
                  }}
                </q-tooltip>
              </q-btn>
            </div>
          </q-td>
        </template>
      </q-table>
    </section>

    <q-dialog v-model="createDialogOpen">
      <q-card class="edit-dialog">
        <q-card-section>
          <div class="text-h6">Add provider key</div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="dialog-form">
            <q-select
              v-model="form.config_type"
              :options="typeOptions"
              emit-value
              map-options
              label="Config type"
              outlined
              dense
              @update:model-value="onTypeChanged"
            />
            <q-select
              v-model="form.provider"
              :options="availableProviderOptions"
              emit-value
              map-options
              label="Provider"
              outlined
              dense
            />
            <q-input v-model="form.name" label="Config name" outlined dense autofocus />
            <q-input
              v-model="form.api_key"
              label="API key"
              type="password"
              outlined
              dense
              autocomplete="off"
            >
              <template #prepend>
                <q-icon name="key" />
              </template>
            </q-input>
            <q-select
              v-if="form.config_type === 'embedding'"
              v-model="form.embedding_model"
              :options="embeddingModelOptions"
              emit-value
              map-options
              label="Embedding model"
              outlined
              dense
            />
            <q-input v-else v-model="form.chat_model" label="Chat model" outlined dense />
            <q-input v-model="form.base_url" label="Base URL" outlined dense />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Cancel" no-caps :disable="busy" v-close-popup />
            <q-btn
              type="submit"
              color="primary"
              icon="encrypted"
              label="Save encrypted"
              :loading="busy"
              no-caps
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="edit-dialog">
        <q-card-section>
          <div class="text-h6">Delete provider config</div>
        </q-card-section>
        <q-card-section class="dialog-form">
          <p class="confirm-copy">
            Delete <strong>{{ deleteTarget?.name }}</strong
            >? The encrypted provider key will be removed from the database.
          </p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" no-caps :disable="busy" @click="deleteDialogOpen = false" />
          <q-btn
            color="negative"
            icon="delete"
            label="Delete"
            :loading="busy"
            no-caps
            @click="confirmDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { useQuasar, type QTableColumn } from 'quasar';
import { computed, reactive, ref } from 'vue';

import type { LlmConfigType, LlmProvider, LlmProviderConfig } from '@/services/api';

defineProps<{
  configs: LlmProviderConfig[];
  busy: boolean;
}>();

const $q = useQuasar();

const emit = defineEmits<{
  createConfig: [
    payload: {
      name: string;
      provider: LlmProvider;
      config_type: LlmConfigType;
      api_key: string;
      base_url?: string | null;
      embedding_model?: string | null;
      chat_model?: string | null;
    },
  ];
  deleteConfig: [configId: string];
}>();

const providerOptions: { label: string; value: LlmProvider }[] = [
  { label: 'Google Gemini', value: 'google' },
];
const embeddingModelOptions = [
  { label: 'Gemini Embedding 2', value: 'gemini-embedding-2' },
  { label: 'Gemini Embedding 001', value: 'gemini-embedding-001' },
];
const typeOptions: { label: string; value: LlmConfigType }[] = [
  { label: 'Embedding', value: 'embedding' },
  { label: 'Chat LLM', value: 'chat_llm' },
];
const availableProviderOptions = computed(() =>
  form.config_type === 'embedding'
    ? providerOptions.filter((option) => option.value !== 'anthropic')
    : providerOptions.filter((option) => option.value !== 'voyage'),
);

const createDialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const deleteTarget = ref<LlmProviderConfig | null>(null);
const form: {
  name: string;
  provider: LlmProvider;
  config_type: LlmConfigType;
  api_key: string;
  base_url: string;
  embedding_model: string;
  chat_model: string;
} = reactive({
  name: '',
  provider: 'google',
  config_type: 'embedding',
  api_key: '',
  base_url: 'https://generativelanguage.googleapis.com/v1beta',
  embedding_model: 'gemini-embedding-2',
  chat_model: '',
});

const columns: QTableColumn<LlmProviderConfig>[] = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'provider', label: 'Provider', field: 'provider', align: 'left', sortable: true },
  { name: 'purpose', label: 'Type', field: 'purpose', align: 'left', sortable: true },
  { name: 'api_key', label: 'Key', field: 'api_key_hint', align: 'left' },
  {
    name: 'embedding_model',
    label: 'Model',
    field: (row) => row.embedding_model || row.chat_model || '',
    align: 'left',
  },
  { name: 'status', label: 'Status', field: 'is_active', align: 'left' },
  { name: 'updated', label: 'Updated', field: 'updated_at', align: 'left', sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' },
];
const visibleColumns = computed(() => {
  if ($q.screen.lt.sm) return ['name', 'provider', 'purpose', 'status', 'actions'];
  if ($q.screen.lt.lg) return ['name', 'provider', 'purpose', 'embedding_model', 'actions'];
  return columns.map((column) => column.name);
});

function openCreateDialog() {
  form.name = '';
  form.provider = 'google';
  form.config_type = 'embedding';
  form.api_key = '';
  form.base_url = 'https://generativelanguage.googleapis.com/v1beta';
  form.embedding_model = 'gemini-embedding-2';
  form.chat_model = '';
  createDialogOpen.value = true;
}

function submitCreate() {
  const model = form.config_type === 'embedding' ? form.embedding_model : form.chat_model;
  if (!form.name.trim() || !form.api_key.trim() || !model.trim()) return;
  emit('createConfig', {
    name: form.name,
    provider: form.provider,
    config_type: form.config_type,
    api_key: form.api_key,
    base_url: form.base_url || null,
    embedding_model: form.embedding_model || null,
    chat_model: form.chat_model || null,
  });
  createDialogOpen.value = false;
}

function openDeleteDialog(config: LlmProviderConfig) {
  deleteTarget.value = config;
  deleteDialogOpen.value = true;
}

function confirmDelete() {
  if (!deleteTarget.value) return;
  emit('deleteConfig', deleteTarget.value.id);
  deleteDialogOpen.value = false;
  deleteTarget.value = null;
}

function providerLabel(provider: LlmProvider) {
  return providerOptions.find((option) => option.value === provider)?.label || provider;
}

function typeLabel(type: LlmConfigType) {
  return type === 'embedding' ? 'Embedding' : 'Chat LLM';
}

function onTypeChanged() {
  form.embedding_model = 'gemini-embedding-2';
  form.chat_model = '';
  if (!availableProviderOptions.value.some((option) => option.value === form.provider)) {
    form.provider = availableProviderOptions.value[0]?.value || 'google';
  }
}
</script>
