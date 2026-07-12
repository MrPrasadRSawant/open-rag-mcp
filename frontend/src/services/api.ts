export type User = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type DocumentGroup = {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  llm_config_id: string | null;
  llm_config_name: string | null;
  created_at: string;
  updated_at: string;
};

export type DeletedDocumentGroup = {
  id: string;
  deleted: boolean;
  documents_deleted: number;
  api_keys_deleted: number;
};

export type DocumentItem = {
  id: string;
  owner_id: string;
  group_id: string;
  title: string;
  source_name: string | null;
  content_type: string;
  status: string;
  error_message: string | null;
  extra_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  chunk_count: number;
  processing_job_id: string | null;
};

export type DeletedDocument = {
  id: string;
  group_id: string;
  deleted: boolean;
  chunks_deleted: number;
  jobs_deleted: number;
};

export type ProcessingJob = {
  id: string;
  owner_id: string;
  document_id: string;
  job_type: string;
  status: string;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type SearchResult = {
  chunk_id: string;
  document_id: string;
  group_id: string;
  text: string;
  score: number;
  vector_score: number | null;
  lexical_score: number | null;
  metadata: Record<string, unknown>;
};

export type SearchOptions = {
  limit?: number;
  candidate_limit?: number;
  rerank?: boolean;
  lexical_weight?: number;
  diversity?: boolean;
  diversity_lambda?: number;
  min_score?: number | null;
};

export type ApiKey = {
  id: string;
  name: string;
  group_id: string | null;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
};

export type CreatedApiKey = ApiKey & {
  api_key: string;
};

export type LlmProvider =
  | 'internal'
  | 'openai'
  | 'azure_openai'
  | 'anthropic'
  | 'google'
  | 'cohere'
  | 'mistral'
  | 'voyage'
  | 'custom';

export type LlmConfigType = 'embedding' | 'chat_llm';

export type LlmProviderConfig = {
  id: string;
  name: string;
  provider: LlmProvider;
  purpose: LlmConfigType;
  api_key_hint: string | null;
  base_url: string | null;
  embedding_model: string | null;
  chat_model: string | null;
  in_use_by_groups: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AgentProfile = {
  id: string;
  user_id: string;
  group_id: string;
  llm_config_id: string;
  name: string;
  instructions: string;
  public_key: string;
  allowed_origins: string[];
  history_enabled: boolean;
  num_history_runs: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AgentPayload = {
  name: string;
  group_id: string;
  llm_config_id: string;
  instructions: string;
  allowed_origins: string[];
  history_enabled: boolean;
  num_history_runs: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

type JsonBody = unknown;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function register(payload: {
  email: string;
  password: string;
  full_name?: string | null;
}): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/register', {
    method: 'POST',
    body: payload,
  });
}

export async function login(payload: { email: string; password: string }): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: payload,
  });
}

export async function getProfile(token: string): Promise<User> {
  return request<User>('/auth/me', { token });
}

export async function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>('/health');
}

export async function listGroups(token: string): Promise<DocumentGroup[]> {
  return request<DocumentGroup[]>('/document-groups', { token });
}

export async function createGroup(
  token: string,
  payload: { name: string; description?: string | null; llm_config_id: string },
): Promise<DocumentGroup> {
  return request<DocumentGroup>('/document-groups', {
    method: 'POST',
    token,
    body: payload,
  });
}

export async function updateGroup(
  token: string,
  groupId: string,
  payload: { name?: string; description?: string | null },
): Promise<DocumentGroup> {
  return request<DocumentGroup>(`/document-groups/${groupId}`, {
    method: 'PATCH',
    token,
    body: payload,
  });
}

export async function deleteGroup(token: string, groupId: string): Promise<DeletedDocumentGroup> {
  return request<DeletedDocumentGroup>(`/document-groups/${groupId}`, {
    method: 'DELETE',
    token,
  });
}

export async function listDocuments(token: string, groupId: string): Promise<DocumentItem[]> {
  return request<DocumentItem[]>(`/document-groups/${groupId}/documents`, { token });
}

export async function createTextDocument(
  token: string,
  groupId: string,
  payload: { title: string; text: string; metadata?: Record<string, unknown> },
): Promise<DocumentItem> {
  return request<DocumentItem>(`/document-groups/${groupId}/documents`, {
    method: 'POST',
    token,
    body: payload,
  });
}

export async function uploadDocument(
  token: string,
  groupId: string,
  payload: { title?: string; file: File },
): Promise<DocumentItem> {
  const form = new FormData();
  form.append('file', payload.file);
  if (payload.title) {
    form.append('title', payload.title);
  }

  return request<DocumentItem>(`/document-groups/${groupId}/documents/upload`, {
    method: 'POST',
    token,
    form,
  });
}

export async function updateDocument(
  token: string,
  groupId: string,
  documentId: string,
  payload: { title?: string },
): Promise<DocumentItem> {
  return request<DocumentItem>(`/document-groups/${groupId}/documents/${documentId}`, {
    method: 'PATCH',
    token,
    body: payload,
  });
}

export async function deleteDocument(
  token: string,
  groupId: string,
  documentId: string,
): Promise<DeletedDocument> {
  return request<DeletedDocument>(`/document-groups/${groupId}/documents/${documentId}`, {
    method: 'DELETE',
    token,
  });
}

export async function getJob(token: string, jobId: string): Promise<ProcessingJob> {
  return request<ProcessingJob>(`/jobs/${jobId}`, { token });
}

export async function searchDocuments(
  token: string,
  payload: { query: string; group_ids?: string[] } & SearchOptions,
): Promise<{ query: string; results: SearchResult[] }> {
  return request<{ query: string; results: SearchResult[] }>('/search', {
    method: 'POST',
    token,
    body: payload,
  });
}

export async function listApiKeys(token: string): Promise<ApiKey[]> {
  return request<ApiKey[]>('/api-keys', { token });
}

export async function createApiKey(
  token: string,
  payload: { name: string; group_id: string },
): Promise<CreatedApiKey> {
  return request<CreatedApiKey>('/api-keys', {
    method: 'POST',
    token,
    body: payload,
  });
}

export async function revokeApiKey(token: string, apiKeyId: string): Promise<ApiKey> {
  return request<ApiKey>(`/api-keys/${apiKeyId}`, {
    method: 'DELETE',
    token,
  });
}

export async function listAgents(token: string): Promise<AgentProfile[]> {
  return request<AgentProfile[]>('/agents', { token });
}

export async function createAgent(token: string, payload: AgentPayload): Promise<AgentProfile> {
  return request<AgentProfile>('/agents', { method: 'POST', token, body: payload });
}

export async function updateAgent(
  token: string,
  agentId: string,
  payload: Partial<
    Pick<
      AgentProfile,
      | 'name'
      | 'instructions'
      | 'allowed_origins'
      | 'history_enabled'
      | 'num_history_runs'
      | 'is_active'
    >
  >,
): Promise<AgentProfile> {
  return request<AgentProfile>(`/agents/${agentId}`, {
    method: 'PATCH',
    token,
    body: payload,
  });
}

export async function deleteAgent(token: string, agentId: string): Promise<AgentProfile> {
  return request<AgentProfile>(`/agents/${agentId}`, { method: 'DELETE', token });
}

export async function listLlmConfigs(token: string): Promise<LlmProviderConfig[]> {
  return request<LlmProviderConfig[]>('/llm-configs', { token });
}

export async function createLlmConfig(
  token: string,
  payload: {
    name: string;
    provider: LlmProvider;
    config_type: LlmConfigType;
    api_key: string;
    base_url?: string | null;
    embedding_model?: string | null;
    chat_model?: string | null;
  },
): Promise<LlmProviderConfig> {
  return request<LlmProviderConfig>('/llm-configs', {
    method: 'POST',
    token,
    body: payload,
  });
}

export async function deleteLlmConfig(token: string, configId: string): Promise<LlmProviderConfig> {
  return request<LlmProviderConfig>(`/llm-configs/${configId}`, {
    method: 'DELETE',
    token,
  });
}

async function request<T>(
  path: string,
  options: {
    method?: string;
    token?: string;
    body?: JsonBody;
    form?: FormData;
  } = {},
): Promise<T> {
  const headers = new Headers();
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }
  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  const requestOptions: RequestInit = {
    method: options.method || 'GET',
    headers,
  };
  if (options.body !== undefined) {
    requestOptions.body = JSON.stringify(options.body);
  } else if (options.form) {
    requestOptions.body = options.form;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, requestOptions);

  const contentType = response.headers.get('content-type') || '';
  const data: unknown = contentType.includes('application/json') ? await response.json() : null;

  if (!response.ok) {
    const message =
      data && typeof data === 'object' && 'detail' in data
        ? String(data.detail)
        : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return data as T;
}
