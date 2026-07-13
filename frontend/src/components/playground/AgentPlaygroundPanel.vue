<template>
  <div class="screen-stack playground-screen">
    <section class="screen-hero playground-hero">
      <div>
        <div class="eyebrow">Agent Playground</div>
        <h1>Talk with your agents</h1>
        <p>Test instructions, retrieval, conversation history, and streamed responses.</p>
      </div>
      <q-btn
        color="primary"
        icon="add_comment"
        label="New conversation"
        no-caps
        :disable="!selectedAgent"
        @click="newConversation"
      />
    </section>

    <section class="workspace-panel playground-selectors">
      <q-select
        v-model="currentGroupId"
        :options="groupOptions"
        emit-value
        map-options
        label="Document group"
        outlined
        dense
      />
      <q-select
        v-model="selectedAgentId"
        :options="agentOptions"
        emit-value
        map-options
        label="AI agent"
        outlined
        dense
        :disable="!agentOptions.length"
      />
    </section>

    <q-banner
      v-if="selectedAgent && !selectedAgent.history_enabled"
      class="feedback-banner feedback-banner-error"
    >
      Conversation history is disabled for this agent. Messages remain available only until this
      screen is changed.
    </q-banner>

    <section class="playground-layout">
      <aside class="workspace-panel playground-sessions">
        <div class="panel-heading">
          <div>
            <h2>Conversations</h2>
            <p>{{ sessions.length }} saved sessions</p>
          </div>
          <q-btn flat round dense icon="refresh" :disable="!selectedAgent" @click="loadSessions" />
        </div>
        <q-list v-if="sessions.length" class="session-list" separator>
          <q-item
            v-for="item in sessions"
            :key="item.id"
            clickable
            :active="item.id === currentSessionId"
            active-class="selected-list-item"
            @click="openSession(item.id)"
          >
            <q-item-section>
              <q-item-label lines="1">{{ item.name }}</q-item-label>
              <q-item-label caption
                >{{ formatSessionDate(item.updated_at) }} ·
                {{ item.message_count }} messages</q-item-label
              >
            </q-item-section>
            <q-item-section side>
              <q-btn flat round dense icon="more_vert" @click.stop>
                <q-menu>
                  <q-list dense style="min-width: 130px">
                    <q-item clickable v-close-popup @click="openRename(item)"
                      ><q-item-section avatar><q-icon name="edit" /></q-item-section
                      ><q-item-section>Rename</q-item-section></q-item
                    >
                    <q-item clickable v-close-popup @click="openDelete(item)"
                      ><q-item-section avatar
                        ><q-icon name="delete" color="negative" /></q-item-section
                      ><q-item-section>Delete</q-item-section></q-item
                    >
                  </q-list>
                </q-menu>
              </q-btn>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="empty-state">
          <q-icon name="forum" /><span>No saved conversations.</span>
        </div>
      </aside>

      <div class="workspace-panel playground-chat">
        <header class="playground-chat-head">
          <div>
            <strong>{{ selectedAgent?.name || 'Select an agent' }}</strong
            ><span>{{ chatStatus }}</span>
          </div>
          <q-btn
            v-if="busy"
            flat
            round
            dense
            color="negative"
            icon="stop_circle"
            @click="stopGeneration"
            ><q-tooltip>Stop generation</q-tooltip></q-btn
          >
        </header>

        <div ref="messageViewport" class="playground-messages" aria-live="polite">
          <div v-if="!selectedAgent" class="playground-empty">
            <q-icon name="smart_toy" size="38px" /><strong
              >Select a document group and AI agent</strong
            >
          </div>
          <div v-else-if="!messages.length" class="playground-empty">
            <q-icon name="chat_bubble_outline" size="38px" /><strong
              >Start a new conversation</strong
            ><span>Ask a question about the selected group’s documents.</span>
          </div>
          <article
            v-for="message in messages"
            :key="message.id"
            class="playground-message"
            :class="message.role"
          >
            <div class="message-avatar">
              <q-icon :name="message.role === 'user' ? 'person' : 'smart_toy'" />
            </div>
            <div class="message-body">
              <div
                v-if="message.role === 'assistant'"
                class="markdown-response"
                v-html="markdown(message.content)"
              ></div>
              <div v-else class="user-response">{{ message.content }}</div>
              <div
                v-if="message.role === 'assistant' && (message.latency || message.totalTokens)"
                class="message-metrics"
              >
                <span v-if="message.latency">{{ message.latency.toFixed(2) }}s</span>
                <span v-if="message.totalTokens">{{ message.totalTokens }} tokens</span>
              </div>
              <div
                v-if="message.role === 'assistant' && message.sources?.length"
                class="message-sources"
              >
                <button
                  type="button"
                  class="sources-toggle"
                  @click="message.sourcesExpanded = !message.sourcesExpanded"
                >
                  <span>Sources ({{ message.sources.length }})</span>
                  <q-icon :name="message.sourcesExpanded ? 'expand_less' : 'expand_more'" />
                </button>
                <div v-show="message.sourcesExpanded" class="sources-list">
                  <div v-for="source in message.sources" :key="source.chunkId || source.documentId">
                    <b class="source-number">{{ source.label }}</b>
                    <span>
                      <strong>{{ source.title || 'Document' }}</strong>
                      <small>{{ source.excerpt }}</small>
                    </span>
                    <small v-if="source.score !== null"
                      >{{ Math.round(source.score * 100) }}%</small
                    >
                  </div>
                </div>
              </div>
            </div>
          </article>
          <div v-if="toolActivity.length" class="tool-activity">
            <div v-for="tool in toolActivity" :key="tool.id">
              <q-spinner v-if="tool.active" size="14px" /><q-icon
                v-else
                name="check_circle"
                color="positive"
              /><span>{{ tool.label }}</span>
            </div>
          </div>
        </div>

        <form class="playground-composer" @submit.prevent="sendMessage">
          <q-input
            v-model="draft"
            type="textarea"
            autogrow
            outlined
            placeholder="Ask the agent..."
            :disable="!selectedAgent || busy"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <q-btn
            type="submit"
            color="primary"
            round
            icon="send"
            :disable="!draft.trim() || !selectedAgent || busy"
            ><q-tooltip>Send message</q-tooltip></q-btn
          >
        </form>
      </div>
    </section>

    <q-dialog v-model="renameDialogOpen">
      <q-card class="edit-dialog"
        ><q-card-section><div class="text-h6">Rename conversation</div></q-card-section
        ><q-form @submit.prevent="renameConversation"
          ><q-card-section
            ><q-input
              v-model="sessionName"
              label="Conversation name"
              outlined
              dense
              autofocus /></q-card-section
          ><q-card-actions align="right"
            ><q-btn flat label="Cancel" no-caps v-close-popup /><q-btn
              type="submit"
              color="primary"
              label="Rename"
              no-caps /></q-card-actions></q-form
      ></q-card>
    </q-dialog>
    <q-dialog v-model="deleteDialogOpen">
      <q-card class="edit-dialog"
        ><q-card-section><div class="text-h6">Delete conversation</div></q-card-section
        ><q-card-section
          >Delete <strong>{{ sessionTarget?.name }}</strong> and its complete
          history?</q-card-section
        ><q-card-actions align="right"
          ><q-btn flat label="Cancel" no-caps v-close-popup /><q-btn
            color="negative"
            icon="delete"
            label="Delete"
            no-caps
            @click="deleteConversation" /></q-card-actions
      ></q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { computed, nextTick, ref, watch } from 'vue';

import {
  deleteAgentSession,
  getAgentSession,
  listAgentSessions,
  renameAgentSession,
  streamPlaygroundAgent,
  type AgentCitation,
  type AgentProfile,
  type AgentSessionSummary,
  type AgentStreamEvent,
} from '@/services/api';
import type { GroupOption } from '@/types/workspace';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  latency?: number | undefined;
  totalTokens?: number | undefined;
  sources?:
    | Array<{
        number: number;
        label: string;
        documentId: string;
        chunkId: string | null;
        title: string;
        excerpt: string;
        score: number | null;
      }>
    | undefined;
  sourcesExpanded?: boolean | undefined;
};
type ToolActivity = { id: string; label: string; active: boolean };

const props = defineProps<{
  agents: AgentProfile[];
  groupOptions: GroupOption[];
  selectedGroupId: string | null;
  token: string;
}>();
const emit = defineEmits<{ selectGroup: [groupId: string]; error: [message: string] }>();
const selectedAgentId = ref<string | null>(null);
const sessions = ref<AgentSessionSummary[]>([]);
const currentSessionId = ref<string>(crypto.randomUUID());
const messages = ref<ChatMessage[]>([]);
const toolActivity = ref<ToolActivity[]>([]);
const draft = ref('');
const busy = ref(false);
const chatStatus = ref('Ready');
const messageViewport = ref<HTMLElement | null>(null);
const renameDialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const sessionTarget = ref<AgentSessionSummary | null>(null);
const sessionName = ref('');
let controller: AbortController | null = null;
let sessionWasNew = true;

marked.setOptions({ breaks: true, gfm: true });
const filteredAgents = computed(() =>
  props.agents.filter((agent) => agent.group_id === props.selectedGroupId && agent.is_active),
);
const agentOptions = computed(() =>
  filteredAgents.value.map((agent) => ({ label: agent.name, value: agent.id })),
);
const selectedAgent = computed(
  () => filteredAgents.value.find((agent) => agent.id === selectedAgentId.value) || null,
);
const currentGroupId = computed({
  get: () => props.selectedGroupId,
  set: (value) => value && emit('selectGroup', value),
});

watch(
  filteredAgents,
  (items) => {
    selectedAgentId.value = items.some((item) => item.id === selectedAgentId.value)
      ? selectedAgentId.value
      : items[0]?.id || null;
  },
  { immediate: true },
);
watch(selectedAgentId, () => {
  newConversation();
  void loadSessions();
});

async function loadSessions() {
  if (!selectedAgent.value) {
    sessions.value = [];
    return;
  }
  try {
    sessions.value = await listAgentSessions(props.token, selectedAgent.value.id);
  } catch (error) {
    reportError(error);
  }
}
async function openSession(sessionId: string) {
  if (!selectedAgent.value || busy.value) return;
  try {
    const detail = await getAgentSession(props.token, selectedAgent.value.id, sessionId);
    currentSessionId.value = detail.id;
    messages.value = detail.messages.map((item) => ({
      id: crypto.randomUUID(),
      role: item.role,
      content: item.content,
      latency: item.latency || undefined,
      totalTokens: (item.input_tokens || 0) + (item.output_tokens || 0) || undefined,
    }));
    sessionWasNew = false;
    await scrollToLatest();
  } catch (error) {
    reportError(error);
  }
}
function newConversation() {
  stopGeneration();
  currentSessionId.value = crypto.randomUUID();
  messages.value = [];
  toolActivity.value = [];
  draft.value = '';
  chatStatus.value = 'Ready';
  sessionWasNew = true;
}
async function sendMessage() {
  const content = draft.value.trim();
  if (!content || !selectedAgent.value || busy.value) return;
  const firstMessage = messages.value.length === 0;
  messages.value.push({ id: crypto.randomUUID(), role: 'user', content });
  const response: ChatMessage = { id: crypto.randomUUID(), role: 'assistant', content: '' };
  messages.value.push(response);
  draft.value = '';
  toolActivity.value = [];
  busy.value = true;
  chatStatus.value = 'Thinking...';
  controller = new AbortController();
  await scrollToLatest();
  try {
    await streamPlaygroundAgent(
      props.token,
      selectedAgent.value.id,
      { message: content, session_id: currentSessionId.value },
      (event) => handleEvent(event, response),
      controller.signal,
    );
    chatStatus.value = 'Ready';
    if (!response.content) response.content = 'No response content was returned.';
    if (selectedAgent.value.history_enabled) {
      if (firstMessage && sessionWasNew)
        await renameAgentSession(
          props.token,
          selectedAgent.value.id,
          currentSessionId.value,
          content.slice(0, 60),
        );
      sessionWasNew = false;
      await loadSessions();
    }
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      response.content += '\n\n_Response stopped._';
      chatStatus.value = 'Stopped';
    } else {
      response.content = `Unable to complete the response: ${(error as Error).message}`;
      chatStatus.value = 'Failed';
      reportError(error);
    }
  } finally {
    busy.value = false;
    controller = null;
    await scrollToLatest();
  }
}
function handleEvent(event: AgentStreamEvent, response: ChatMessage) {
  if (event.event === 'RunContent' && event.content) response.content += event.content;
  if (event.event === 'citations' && event.citations) {
    response.sources = [...(response.sources || []), ...event.citations.map(mapCitation)];
  }
  if (event.event === 'ToolCallStarted')
    toolActivity.value.push({
      id: event.tool?.tool_name || crypto.randomUUID(),
      label:
        event.tool?.tool_name === 'search_knowledge'
          ? 'Searching group documents'
          : `Running ${event.tool?.tool_name || 'tool'}`,
      active: true,
    });
  if (event.event === 'ToolCallCompleted') {
    toolActivity.value = toolActivity.value.map((item) => ({ ...item, active: false }));
    if (event.tool?.tool_name === 'search_knowledge' && event.tool.result) {
      try {
        const results = JSON.parse(event.tool.result) as Array<{
          document_id: string;
          title: string | null;
          score: number;
        }>;
        if (response.sources?.length) return;
        response.sources = Array.from(
          new Map(
            results.map((result) => [
              result.document_id,
              {
                number: results.indexOf(result) + 1,
                label: `[${results.indexOf(result) + 1}]`,
                documentId: result.document_id,
                chunkId: null,
                title: result.title || 'Document',
                excerpt: '',
                score: result.score,
              },
            ]),
          ).values(),
        );
      } catch {
        response.sources = [];
      }
    }
  }
  if (event.event === 'RunCompleted') {
    const metrics = event.metrics as { duration?: number; total_tokens?: number } | undefined;
    response.latency = metrics?.duration;
    response.totalTokens = metrics?.total_tokens;
  }
  if (event.event === 'error') throw new Error(event.message || 'Agent run failed');
  void scrollToLatest();
}
function stopGeneration() {
  controller?.abort();
}
function openRename(item: AgentSessionSummary) {
  sessionTarget.value = item;
  sessionName.value = item.name;
  renameDialogOpen.value = true;
}
async function renameConversation() {
  if (!selectedAgent.value || !sessionTarget.value || !sessionName.value.trim()) return;
  try {
    await renameAgentSession(
      props.token,
      selectedAgent.value.id,
      sessionTarget.value.id,
      sessionName.value,
    );
    renameDialogOpen.value = false;
    await loadSessions();
  } catch (error) {
    reportError(error);
  }
}
function openDelete(item: AgentSessionSummary) {
  sessionTarget.value = item;
  deleteDialogOpen.value = true;
}
async function deleteConversation() {
  if (!selectedAgent.value || !sessionTarget.value) return;
  try {
    await deleteAgentSession(props.token, selectedAgent.value.id, sessionTarget.value.id);
    if (currentSessionId.value === sessionTarget.value.id) newConversation();
    deleteDialogOpen.value = false;
    await loadSessions();
  } catch (error) {
    reportError(error);
  }
}
function markdown(content: string) {
  const rendered = marked.parse(content) as string;
  return DOMPurify.sanitize(
    rendered.replace(/\[(\d+)]/g, '<sup class="citation-marker">[$1]</sup>'),
  );
}
function mapCitation(source: AgentCitation) {
  return {
    number: source.number,
    label: source.label,
    documentId: source.document_id,
    chunkId: source.chunk_id,
    title: source.title,
    excerpt: source.excerpt,
    score: source.score,
  };
}
function formatSessionDate(value: number | null) {
  return value ? new Date(value * 1000).toLocaleString() : 'Recently';
}
async function scrollToLatest() {
  await nextTick();
  if (messageViewport.value) messageViewport.value.scrollTop = messageViewport.value.scrollHeight;
}
function reportError(error: unknown) {
  emit('error', error instanceof Error ? error.message : 'Playground request failed.');
}
</script>
