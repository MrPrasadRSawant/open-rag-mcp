<template>
  <q-layout view="lHh Lpr lFf" class="app-shell">
    <app-topbar
      v-if="session.isAuthenticated"
      :api-online="apiOnline"
      :user-email="session.user?.email || ''"
      @toggle-menu="leftDrawerOpen = !leftDrawerOpen"
      @sign-out="signOut"
    />

    <q-drawer
      v-if="session.isAuthenticated"
      v-model="leftDrawerOpen"
      show-if-above
      bordered
      :width="280"
      class="app-drawer"
    >
      <app-menu />
    </q-drawer>

    <q-page-container :class="{ 'auth-page-container': !session.isAuthenticated }">
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import AppMenu from '@/components/app/AppMenu.vue';
import AppTopbar from '@/components/app/AppTopbar.vue';
import { getHealth } from '@/services/api';
import { useSessionStore } from '@/stores/session-store';

const router = useRouter();
const session = useSessionStore();
const leftDrawerOpen = ref(false);
const apiOnline = ref(false);

onMounted(async () => {
  await session.restore();
  try {
    const health = await getHealth();
    apiOnline.value = health.status === 'ok';
  } catch {
    apiOnline.value = false;
  }
});

async function signOut() {
  session.logout();
  await router.push({ name: 'dashboard' });
}
</script>
