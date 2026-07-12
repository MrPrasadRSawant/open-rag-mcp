import { computed, ref } from 'vue';

import {
  createApiKey,
  createGroup,
  createTextDocument,
  deleteDocument,
  deleteGroup,
  getJob,
  listApiKeys,
  listDocuments,
  listGroups,
  revokeApiKey,
  searchDocuments,
  updateDocument,
  updateGroup,
  uploadDocument,
  type ApiKey,
  type DocumentGroup,
  type DocumentItem,
  type ProcessingJob,
  type SearchResult,
} from '@/services/api';
import type { useSessionStore } from '@/stores/session-store';
import type { GroupOption } from '@/types/workspace';

type SessionStore = ReturnType<typeof useSessionStore>;

export function useWorkspace(session: SessionStore) {
  const groups = ref<DocumentGroup[]>([]);
  const documents = ref<DocumentItem[]>([]);
  const jobs = ref<ProcessingJob[]>([]);
  const apiKeys = ref<ApiKey[]>([]);
  const searchResults = ref<SearchResult[]>([]);
  const selectedGroupId = ref<string | null>(null);
  const createdKey = ref('');
  const errorMessage = ref('');
  const statusMessage = ref('');
  const loading = ref(false);
  const actionBusy = ref(false);

  const selectedGroup = computed(
    () => groups.value.find((group) => group.id === selectedGroupId.value) || null,
  );

  const groupOptions = computed<GroupOption[]>(() =>
    groups.value.map((group) => ({ label: group.name, value: group.id })),
  );

  const totalChunks = computed(() =>
    documents.value.reduce((total, document) => total + document.chunk_count, 0),
  );

  const completedDocuments = computed(
    () => documents.value.filter((document) => document.status === 'completed').length,
  );

  const activeJobs = computed(
    () => jobs.value.filter((job) => job.status === 'queued' || job.status === 'processing').length,
  );

  const activeApiKeys = computed(() => apiKeys.value.filter((key) => !key.revoked_at).length);

  async function loadWorkspace() {
    if (!session.token) return;
    loading.value = true;
    try {
      groups.value = await listGroups(session.token);
      if (!selectedGroupId.value && groups.value[0]) {
        selectedGroupId.value = groups.value[0].id;
      }
      await Promise.all([loadDocuments(), loadApiKeys()]);
    } catch (error) {
      setError(error);
    } finally {
      loading.value = false;
    }
  }

  async function selectGroup(groupId: string) {
    selectedGroupId.value = groupId;
    await loadDocuments();
  }

  async function loadDocuments() {
    if (!session.token || !selectedGroupId.value) {
      documents.value = [];
      return;
    }
    documents.value = await listDocuments(session.token, selectedGroupId.value);
  }

  async function createWorkspaceGroup(payload: { name: string; description?: string | null }) {
    if (!session.token || !payload.name.trim()) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const group = await createGroup(session.token, payload);
      selectedGroupId.value = group.id;
      statusMessage.value = 'Document group created.';
      await loadWorkspace();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function updateWorkspaceGroup(
    groupId: string,
    payload: { name?: string; description?: string | null },
  ) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      await updateGroup(session.token, groupId, payload);
      statusMessage.value = 'Document group updated.';
      await loadWorkspace();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function deleteWorkspaceGroup(groupId: string) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      await deleteGroup(session.token, groupId);
      if (selectedGroupId.value === groupId) {
        selectedGroupId.value = null;
      }
      statusMessage.value = 'Document group deleted.';
      await loadWorkspace();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function queueTextDocument(payload: { title: string; text: string }) {
    if (!session.token || !selectedGroupId.value || !payload.title || !payload.text) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const document = await createTextDocument(session.token, selectedGroupId.value, payload);
      statusMessage.value = 'Text document queued for processing.';
      void trackJob(document.processing_job_id);
      await loadDocuments();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function queueUpload(payload: { title?: string; file: File }) {
    if (!session.token || !selectedGroupId.value) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const document = await uploadDocument(session.token, selectedGroupId.value, payload);
      statusMessage.value = 'File queued for processing.';
      void trackJob(document.processing_job_id);
      await loadDocuments();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function updateWorkspaceDocument(documentId: string, payload: { title?: string }) {
    if (!session.token || !selectedGroupId.value) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      await updateDocument(session.token, selectedGroupId.value, documentId, payload);
      statusMessage.value = 'Document updated.';
      await loadDocuments();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function deleteWorkspaceDocument(documentId: string) {
    if (!session.token || !selectedGroupId.value) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      await deleteDocument(session.token, selectedGroupId.value, documentId);
      statusMessage.value = 'Document deleted.';
      await loadDocuments();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function runSearch(query: string) {
    if (!session.token || !query.trim()) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const payload: { query: string; group_ids?: string[]; limit?: number } = {
        query,
        limit: 8,
      };
      if (selectedGroupId.value) {
        payload.group_ids = [selectedGroupId.value];
      }
      const response = await searchDocuments(session.token, payload);
      searchResults.value = response.results;
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function loadApiKeys() {
    if (!session.token) return;
    apiKeys.value = await listApiKeys(session.token);
  }

  async function createWorkspaceApiKey(payload: { name: string; group_id: string }) {
    if (!session.token || !payload.name.trim() || !payload.group_id) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const key = await createApiKey(session.token, payload);
      createdKey.value = key.api_key;
      statusMessage.value =
        'Document-group scoped MCP key created. Copy it now; it is shown only once.';
      await loadApiKeys();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function revokeWorkspaceApiKey(apiKeyId: string) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      await revokeApiKey(session.token, apiKeyId);
      statusMessage.value = 'API key revoked.';
      await loadApiKeys();
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function trackJob(jobId: string | null) {
    if (!session.token || !jobId) return;
    const job = await getJob(session.token, jobId);
    jobs.value = [job, ...jobs.value.filter((item) => item.id !== job.id)].slice(0, 8);
    window.setTimeout(() => void refreshJob(job.id), 1200);
  }

  async function refreshJob(jobId: string) {
    if (!session.token) return;
    const job = await getJob(session.token, jobId);
    jobs.value = jobs.value.map((item) => (item.id === job.id ? job : item));
    if (job.status === 'queued' || job.status === 'processing') {
      window.setTimeout(() => void refreshJob(job.id), 1600);
      return;
    }
    await loadDocuments();
  }

  function clearFeedback() {
    errorMessage.value = '';
    statusMessage.value = '';
  }

  function clearCreatedKey() {
    createdKey.value = '';
  }

  function setError(error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed.';
  }

  return {
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
    completedDocuments,
    activeJobs,
    activeApiKeys,
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
  };
}
