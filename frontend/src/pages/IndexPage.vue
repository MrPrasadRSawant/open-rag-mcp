<template>
  <auth-screen
    v-if="!session.isAuthenticated"
    :busy="authBusy"
    :error="authError"
    @authenticate="submitAuth"
  />

  <q-page v-else class="dashboard-page">
    <div class="workspace-frame">
      <main class="workspace-content">
        <feedback-banner :message="errorMessage" tone="error" @dismiss="errorMessage = ''" />
        <feedback-banner :message="statusMessage" tone="success" @dismiss="statusMessage = ''" />

        <dashboard-panel
          v-if="currentSection === 'dashboard'"
          :groups-count="groups.length"
          :documents-count="documents.length"
          :total-chunks="totalChunks"
          :active-jobs="activeJobs"
          :selected-group-name="selectedGroup?.name || ''"
          :jobs="jobs"
          :loading="loading"
          @refresh="loadWorkspace"
        />

        <document-groups-panel
          v-else-if="currentSection === 'groups'"
          :groups="groups"
          :selected-group-id="selectedGroupId"
          :busy="actionBusy"
          @refresh="loadWorkspace"
          @select-group="selectGroup"
          @create-group="createWorkspaceGroup"
          @update-group="updateWorkspaceGroup"
          @delete-group="deleteWorkspaceGroup"
        />

        <documents-panel
          v-else-if="currentSection === 'documents'"
          :group-options="groupOptions"
          :selected-group-id="selectedGroupId"
          :documents="documents"
          :busy="actionBusy"
          @select-group="selectGroup"
          @queue-text="queueTextDocument"
          @queue-upload="queueUpload"
          @update-document="updateWorkspaceDocument"
          @delete-document="deleteWorkspaceDocument"
          @refresh="loadWorkspace"
        />

        <search-panel
          v-else-if="currentSection === 'search'"
          :group-options="groupOptions"
          :selected-group-id="selectedGroupId"
          :results="searchResults"
          :busy="actionBusy"
          @select-group="selectGroup"
          @search="runSearch"
        />

        <api-keys-panel
          v-else
          :api-keys="apiKeys"
          :group-options="groupOptions"
          :selected-group-id="selectedGroupId"
          :created-key="createdKey"
          :busy="actionBusy"
          @select-group="selectGroup"
          @create-key="createWorkspaceApiKey"
          @revoke-key="revokeWorkspaceApiKey"
          @clear-created-key="clearCreatedKey"
        />
      </main>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import AuthScreen from '@/components/auth/AuthScreen.vue';
import FeedbackBanner from '@/components/common/FeedbackBanner.vue';
import DashboardPanel from '@/components/dashboard/DashboardPanel.vue';
import DocumentsPanel from '@/components/documents/DocumentsPanel.vue';
import DocumentGroupsPanel from '@/components/groups/DocumentGroupsPanel.vue';
import ApiKeysPanel from '@/components/keys/ApiKeysPanel.vue';
import SearchPanel from '@/components/search/SearchPanel.vue';
import { useWorkspace } from '@/composables/useWorkspace';
import { useSessionStore } from '@/stores/session-store';
import type { WorkspaceSection } from '@/types/workspace';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();

const authBusy = ref(false);
const authError = ref('');

const {
  groups,
  documents,
  jobs,
  apiKeys,
  searchResults,
  selectedGroupId,
  selectedGroup,
  groupOptions,
  createdKey,
  errorMessage,
  statusMessage,
  loading,
  actionBusy,
  totalChunks,
  activeJobs,
  loadWorkspace,
  selectGroup,
  createWorkspaceGroup,
  updateWorkspaceGroup,
  deleteWorkspaceGroup,
  queueTextDocument,
  queueUpload,
  updateWorkspaceDocument,
  deleteWorkspaceDocument,
  runSearch,
  createWorkspaceApiKey,
  revokeWorkspaceApiKey,
  clearFeedback,
  clearCreatedKey,
} = useWorkspace(session);

const currentSection = computed<WorkspaceSection>(() => {
  const section = route.meta.section;
  return section === 'groups' ||
    section === 'documents' ||
    section === 'search' ||
    section === 'keys'
    ? section
    : 'dashboard';
});

onMounted(async () => {
  await session.restore();
  if (session.isAuthenticated) {
    await loadWorkspace();
  }
});

watch(
  () => session.isAuthenticated,
  async (isAuthenticated) => {
    if (isAuthenticated) {
      await loadWorkspace();
    }
  },
);

watch(
  () => route.name,
  () => clearFeedback(),
);

async function submitAuth(payload: {
  mode: 'login' | 'register';
  email: string;
  password: string;
  full_name?: string | null;
}) {
  authBusy.value = true;
  authError.value = '';
  try {
    if (payload.mode === 'login') {
      await session.login({ email: payload.email, password: payload.password });
    } else {
      await session.register({
        email: payload.email,
        password: payload.password,
        full_name: payload.full_name || null,
      });
    }
    await loadWorkspace();
    await router.push({ name: 'dashboard' });
  } catch (error) {
    authError.value = error instanceof Error ? error.message : 'Authentication failed.';
  } finally {
    authBusy.value = false;
  }
}
</script>
