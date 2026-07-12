<template>
  <q-header class="app-header">
    <q-toolbar class="toolbar">
      <q-btn
        flat
        dense
        round
        icon="menu"
        aria-label="Menu"
        class="lt-md"
        @click="$emit('toggleMenu')"
      />
      <q-avatar square size="34px" class="brand-mark">
        <q-icon name="hub" size="22px" />
      </q-avatar>
      <div class="brand-block">
        <q-toolbar-title class="brand-title">Open RAG MCP</q-toolbar-title>
        <div class="brand-subtitle">Create a searchable private knowledge base</div>
      </div>
      <q-space />
      <q-chip
        dense
        square
        :color="apiOnline ? 'green-2' : 'red-2'"
        :text-color="apiOnline ? 'green-10' : 'red-10'"
        :icon="apiOnline ? 'check_circle' : 'error'"
      >
        API
      </q-chip>
      <q-btn-dropdown
        flat
        dense
        no-caps
        icon="account_circle"
        :label="userEmail"
        class="account-menu"
      >
        <q-list dense>
          <q-item>
            <q-item-section>
              <q-item-label>{{ userEmail }}</q-item-label>
              <q-item-label caption>Signed in</q-item-label>
            </q-item-section>
          </q-item>
          <q-separator />
          <q-item clickable @click="$emit('signOut')">
            <q-item-section avatar>
              <q-icon name="logout" />
            </q-item-section>
            <q-item-section>Sign out</q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>
    </q-toolbar>
  </q-header>
</template>

<script setup lang="ts">
defineProps<{
  apiOnline: boolean;
  userEmail: string;
}>();

defineEmits<{
  toggleMenu: [];
  signOut: [];
}>();
</script>
