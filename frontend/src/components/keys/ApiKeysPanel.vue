<template>
  <div class="screen-stack">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">Connect To MCP</div>
        <h1>Connect MCP</h1>
        <p>Create a document-group scoped API key and use it with the hosted MCP endpoint.</p>
      </div>
    </section>

    <section class="workspace-panel guide-panel">
      <q-expansion-item icon="terminal" label="MCP connection guide" header-class="guide-header">
        <div class="mcp-config-stack">
          <div class="mcp-config-row">
            <div>
              <span>URL</span>
              <code>{{ mcpEndpoint }}</code>
            </div>
            <q-btn
              flat
              dense
              icon="content_copy"
              :label="copyLabel('endpoint')"
              no-caps
              @click="copyText(mcpEndpoint, 'endpoint')"
            />
          </div>
          <div class="mcp-config-row">
            <div>
              <span>Header</span>
              <code>Authorization: Bearer &lt;your API key&gt;</code>
            </div>
            <q-btn
              flat
              dense
              icon="content_copy"
              :label="copyLabel('headerTemplate')"
              no-caps
              @click="copyText('Authorization: Bearer <your API key>', 'headerTemplate')"
            />
          </div>
          <div class="mcp-config-row">
            <div>
              <span>Client config</span>
              <code>{{ clientConfigTemplate }}</code>
            </div>
            <q-btn
              flat
              dense
              icon="content_copy"
              :label="copyLabel('configTemplate')"
              no-caps
              @click="copyText(clientConfigTemplate, 'configTemplate')"
            />
          </div>
        </div>
        <ol class="guide-list">
          <li>Select the document group this MCP key can access.</li>
          <li>Create the API key and copy it from the popup before closing it.</li>
          <li>Use the MCP URL and Authorization header in your AI platform.</li>
          <li>Do not put the API key in the prompt or in tool arguments.</li>
          <li>MCP search will only return chunks from the selected document group.</li>
        </ol>
      </q-expansion-item>
    </section>

    <section class="workspace-panel document-toolbar">
      <q-select
        v-model="currentGroupId"
        :options="groupOptions"
        emit-value
        map-options
        label="Document group"
        outlined
        dense
        class="toolbar-select"
        :disable="!groupOptions.length"
      />
      <q-btn
        color="primary"
        icon="add"
        label="Create API key"
        :loading="busy"
        :disable="!selectedGroupId"
        no-caps
        @click="createSelectedGroupKey"
      />
    </section>

    <q-banner v-if="!selectedGroupId" rounded class="feedback-banner feedback-banner-error">
      <template #avatar>
        <q-icon name="folder_off" />
      </template>
      Select a document group before creating MCP API keys.
      <template #action>
        <q-btn flat dense icon="folder_open" label="Groups" no-caps :to="{ name: 'groups' }" />
      </template>
    </q-banner>

    <section class="workspace-panel">
      <div class="panel-heading">
        <div>
          <h2>Existing keys</h2>
          <p>{{ filteredApiKeys.length }} keys for {{ selectedGroupLabel }}</p>
        </div>
        <q-icon name="vpn_key" />
      </div>

      <q-list v-if="filteredApiKeys.length" separator class="flush-list">
        <q-item v-for="key in filteredApiKeys" :key="key.id">
          <q-item-section avatar>
            <q-icon :name="key.revoked_at ? 'lock' : 'key'" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ key.name }}</q-item-label>
            <q-item-label caption>
              {{ groupLabel(key.group_id) }} - {{ key.key_prefix }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn
              flat
              round
              dense
              color="negative"
              icon="delete"
              :disable="Boolean(key.revoked_at)"
              @click="$emit('revokeKey', key.id)"
            />
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else class="empty-state">
        <q-icon name="key_off" />
        <span>No API keys issued for this group.</span>
      </div>
    </section>

    <q-dialog v-model="keyDialogOpen" persistent>
      <q-card class="api-key-dialog">
        <q-card-section class="dialog-head">
          <div>
            <div class="eyebrow">One-time secret</div>
            <h2>Copy API key</h2>
            <p>
              This API key is shown only once. Copy it now and store it in your AI platform MCP
              connection settings.
            </p>
          </div>
          <q-icon name="vpn_key" />
        </q-card-section>

        <q-card-section class="secret-stack">
          <div class="secret-block">
            <span>API key</span>
            <div class="secret-copy-field">
              <code>{{ createdKey }}</code>
              <q-btn
                round
                outline
                class="secret-copy-button"
                :color="copiedField === 'key' ? 'positive' : 'primary'"
                :icon="copiedField === 'key' ? 'check_circle' : 'file_copy'"
                :aria-label="copiedField === 'key' ? 'API key copied' : 'Copy API key'"
                @click="copyText(createdKey, 'key')"
              >
                <q-tooltip>{{ copiedField === 'key' ? 'Copied' : 'Copy API key' }}</q-tooltip>
              </q-btn>
            </div>
          </div>

          <q-banner rounded class="created-key-banner">
            <template #avatar>
              <q-icon name="warning" />
            </template>
            Closing this popup removes the visible key from this screen. You cannot view the full
            key again after closing.
          </q-banner>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat icon="close" label="Close" no-caps @click="closeKeyDialog" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { copyToClipboard } from 'quasar';

import type { ApiKey } from '@/services/api';
import type { GroupOption } from '@/types/workspace';

const props = defineProps<{
  apiKeys: ApiKey[];
  groupOptions: GroupOption[];
  selectedGroupId: string | null;
  createdKey: string;
  busy: boolean;
}>();

const emit = defineEmits<{
  createKey: [payload: { name: string; group_id: string }];
  selectGroup: [groupId: string];
  revokeKey: [apiKeyId: string];
  clearCreatedKey: [];
}>();

const keyDialogOpen = ref(false);
const copiedField = ref('');
let copiedTimer: number | null = null;

const mcpEndpoint = normalizeEndpoint(import.meta.env.VITE_MCP_ENDPOINT || `${apiBaseUrl()}/mcp/`);
const clientConfigTemplate = JSON.stringify(
  {
    url: mcpEndpoint,
    headers: {
      Authorization: 'Bearer <your API key>',
    },
  },
  null,
  2,
);
const currentGroupId = computed({
  get: () => props.selectedGroupId,
  set: (value) => {
    if (value) emit('selectGroup', value);
  },
});
const filteredApiKeys = computed(() =>
  props.selectedGroupId
    ? props.apiKeys.filter((key) => key.group_id === props.selectedGroupId)
    : [],
);
const selectedGroupLabel = computed(() =>
  props.selectedGroupId ? groupLabel(props.selectedGroupId) : 'selected group',
);

watch(
  () => props.createdKey,
  (key) => {
    if (key) {
      keyDialogOpen.value = true;
    }
  },
);

function createSelectedGroupKey() {
  if (!props.selectedGroupId) return;
  emit('createKey', {
    name: `MCP key - ${groupLabel(props.selectedGroupId)} - ${new Date().toLocaleString()}`,
    group_id: props.selectedGroupId,
  });
}

function groupLabel(value: string | null) {
  if (!value) return 'No group';
  return props.groupOptions.find((group) => group.value === value)?.label || value;
}

async function copyText(value: string, field: string) {
  if (!value) return;
  await copyToClipboard(value);
  copiedField.value = field;
  if (copiedTimer) {
    window.clearTimeout(copiedTimer);
  }
  copiedTimer = window.setTimeout(() => {
    copiedField.value = '';
  }, 1600);
}

function copyLabel(field: string) {
  return copiedField.value === field ? 'Copied' : 'Copy';
}

function closeKeyDialog() {
  keyDialogOpen.value = false;
  emit('clearCreatedKey');
}

function apiBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) {
    return stripTrailingSlash(import.meta.env.VITE_API_BASE_URL);
  }
  if (window.location.origin.endsWith(':9000')) {
    return window.location.origin.replace(/:9000$/, ':8000');
  }
  return window.location.origin;
}

function normalizeEndpoint(value: string) {
  const trimmed = value.trim();
  if (trimmed.endsWith('/')) return trimmed;
  return `${trimmed}/`;
}

function stripTrailingSlash(value: string) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}
</script>
