<template>
  <div class="app-menu">
    <div class="menu-section-label">Main menu</div>
    <q-list class="menu-list">
      <q-item
        v-for="item in navItems"
        :key="item.name"
        clickable
        exact
        :to="{ name: item.name }"
        class="menu-item"
        active-class="menu-item-active"
      >
        <q-item-section avatar>
          <q-icon :name="item.icon" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ item.label }}</q-item-label>
          <q-item-label caption>{{ item.caption }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>

    <div class="menu-section-label">Use case</div>
    <div class="menu-info-panel">
      <q-icon name="hub" size="20px" />
      <div>
        <div class="menu-info-title">Private RAG for MCP</div>
        <div class="menu-info-copy">
          Create groups, add documents, test search, then connect MCP.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const navItems = [
  {
    name: 'dashboard',
    label: 'Dashboard',
    caption: 'Analytics and status',
    icon: 'space_dashboard',
  },
  {
    name: 'llm',
    label: 'LLM Config',
    caption: 'Set up models first',
    icon: 'tune',
  },
  {
    name: 'groups',
    label: 'Document Groups',
    caption: 'List and manage groups',
    icon: 'folder_open',
  },
  {
    name: 'documents',
    label: 'Documents',
    caption: 'Group-scoped documents',
    icon: 'description',
  },
  {
    name: 'search',
    label: 'Search Bench',
    caption: 'Test retrieval quality',
    icon: 'science',
  },
  {
    name: 'keys',
    label: 'Setup AI Agent',
    caption: 'Agents and integrations',
    icon: 'smart_toy',
  },
  {
    name: 'playground',
    label: 'Agent Playground',
    caption: 'Chat and inspect runs',
    icon: 'forum',
  },
];
</script>
