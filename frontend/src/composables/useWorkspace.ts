import { computed, ref } from 'vue';

import {
  createApiKey,
  createAgent,
  createGroup,
  createLlmConfig,
  createTextDocument,
  deleteDocument,
  deleteAgent,
  deleteGroup,
  deleteLlmConfig,
  getJob,
  listApiKeys,
  listAgents,
  listDocuments,
  listGroups,
  listLlmConfigs,
  revokeApiKey,
  searchDocuments,
  updateDocument,
  updateAgent,
  updateGroup,
  uploadDocument,
  type ApiKey,
  type AgentPayload,
  type AgentProfile,
  type DocumentGroup,
  type DocumentItem,
  type LlmProvider,
  type LlmConfigType,
  type LlmProviderConfig,
  type ProcessingJob,
  type SearchOptions,
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
  const agents = ref<AgentProfile[]>([]);
  const llmConfigs = ref<LlmProviderConfig[]>([]);
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
    const requestToken = session.token;
    loading.value = true;
    try {
      const loadedGroups = await listGroups(requestToken);
      if (session.token !== requestToken) return;
      groups.value = loadedGroups;
      const selectionBelongsToUser = groups.value.some(
        (group) => group.id === selectedGroupId.value,
      );
      if (!selectionBelongsToUser) selectedGroupId.value = groups.value[0]?.id || null;
      await Promise.all([loadDocuments(), loadApiKeys(), loadLlmConfigs(), loadAgents()]);
    } catch (error) {
      setError(error);
    } finally {
      loading.value = false;
    }
  }

  async function selectGroup(groupId: string) {
    if (!groups.value.some((group) => group.id === groupId)) return;
    selectedGroupId.value = groupId;
    await loadDocuments();
  }

  function resetWorkspace() {
    groups.value = [];
    documents.value = [];
    jobs.value = [];
    apiKeys.value = [];
    agents.value = [];
    llmConfigs.value = [];
    searchResults.value = [];
    selectedGroupId.value = null;
    createdKey.value = '';
    errorMessage.value = '';
    statusMessage.value = '';
    loading.value = false;
    actionBusy.value = false;
  }

  async function loadDocuments() {
    if (!session.token || !selectedGroupId.value) {
      documents.value = [];
      return;
    }
    const requestToken = session.token;
    const requestGroupId = selectedGroupId.value;
    const loadedDocuments = await listDocuments(requestToken, requestGroupId);
    if (session.token === requestToken && selectedGroupId.value === requestGroupId) {
      documents.value = loadedDocuments;
    }
  }

  async function createWorkspaceGroup(payload: {
    name: string;
    description?: string | null;
    llm_config_id: string;
  }) {
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
      const deletedGroup = await deleteGroup(session.token, groupId);
      if (!deletedGroup.deleted) {
        throw new Error('Document group was not deleted.');
      }

      groups.value = groups.value.filter((group) => group.id !== deletedGroup.id);
      apiKeys.value = apiKeys.value.filter((key) => key.group_id !== deletedGroup.id);
      if (selectedGroupId.value === deletedGroup.id) {
        selectedGroupId.value = groups.value[0]?.id || null;
        searchResults.value = [];
        jobs.value = [];
        if (selectedGroupId.value) {
          await loadDocuments();
        } else {
          documents.value = [];
        }
      }
      statusMessage.value = `Document group deleted. Removed ${deletedGroup.documents_deleted} document${deletedGroup.documents_deleted === 1 ? '' : 's'}.`;
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
      const deletedDocument = await deleteDocument(
        session.token,
        selectedGroupId.value,
        documentId,
      );
      if (!deletedDocument.deleted) {
        throw new Error('Document was not deleted.');
      }

      documents.value = documents.value.filter((document) => document.id !== deletedDocument.id);
      searchResults.value = searchResults.value.filter(
        (result) => result.document_id !== deletedDocument.id,
      );
      jobs.value = jobs.value.filter((job) => job.document_id !== deletedDocument.id);
      statusMessage.value = `Document deleted. Removed ${deletedDocument.chunks_deleted} indexed chunk${deletedDocument.chunks_deleted === 1 ? '' : 's'}.`;
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function runSearch(query: string, options: SearchOptions = {}) {
    if (!session.token || !query.trim()) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const payload: { query: string; group_ids?: string[] } & SearchOptions = {
        query,
        ...options,
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
    const requestToken = session.token;
    const loadedApiKeys = await listApiKeys(requestToken);
    if (session.token === requestToken) apiKeys.value = loadedApiKeys;
  }

  async function loadAgents() {
    if (!session.token) return;
    const requestToken = session.token;
    const loadedAgents = await listAgents(requestToken);
    if (session.token === requestToken) agents.value = loadedAgents;
  }

  async function createWorkspaceAgent(payload: AgentPayload) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const agent = await createAgent(session.token, payload);
      agents.value = [agent, ...agents.value];
      statusMessage.value = 'AI agent created.';
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function updateWorkspaceAgent(agentId: string, payload: Partial<AgentProfile>) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const agent = await updateAgent(session.token, agentId, payload);
      agents.value = agents.value.map((item) => (item.id === agent.id ? agent : item));
      statusMessage.value = 'AI agent updated.';
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function deleteWorkspaceAgent(agentId: string) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const agent = await deleteAgent(session.token, agentId);
      agents.value = agents.value.filter((item) => item.id !== agent.id);
      statusMessage.value = 'AI agent deleted.';
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function loadLlmConfigs() {
    if (!session.token) return;
    const requestToken = session.token;
    const loadedConfigs = await listLlmConfigs(requestToken);
    if (session.token === requestToken) llmConfigs.value = loadedConfigs;
  }

  async function createWorkspaceLlmConfig(payload: {
    name: string;
    provider: LlmProvider;
    config_type: LlmConfigType;
    api_key: string;
    base_url?: string | null;
    embedding_model?: string | null;
    chat_model?: string | null;
  }) {
    if (!session.token || !payload.name.trim() || !payload.api_key.trim()) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const config = await createLlmConfig(session.token, payload);
      llmConfigs.value = [config, ...llmConfigs.value];
      statusMessage.value = 'LLM provider config saved with encrypted API key.';
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function deleteWorkspaceLlmConfig(configId: string) {
    if (!session.token) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const config = await deleteLlmConfig(session.token, configId);
      llmConfigs.value = llmConfigs.value.filter((item) => item.id !== config.id);
      statusMessage.value = 'LLM provider config deleted.';
    } catch (error) {
      setError(error);
    } finally {
      actionBusy.value = false;
    }
  }

  async function createWorkspaceApiKey(payload: { name: string; group_id: string }) {
    if (!session.token || !payload.name.trim() || !payload.group_id) return;
    clearFeedback();
    actionBusy.value = true;
    try {
      const key = await createApiKey(session.token, payload);
      createdKey.value = key.api_key;
      statusMessage.value = 'Group-scoped API key created. Copy it now; it is shown only once.';
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
    agents,
    llmConfigs,
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
    createWorkspaceAgent,
    updateWorkspaceAgent,
    deleteWorkspaceAgent,
    revokeWorkspaceApiKey,
    createWorkspaceLlmConfig,
    deleteWorkspaceLlmConfig,
    clearFeedback,
    clearCreatedKey,
    resetWorkspace,
  };
}
