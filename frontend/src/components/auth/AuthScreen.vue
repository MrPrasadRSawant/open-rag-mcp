<template>
  <q-page class="auth-page">
    <section class="auth-shell">
      <div class="auth-brand-panel">
        <div class="auth-brand-lockup">
          <q-avatar square size="42px" class="brand-mark auth-brand-mark">
            <q-icon name="hub" size="26px" />
          </q-avatar>
          <div>
            <div class="auth-product">Open RAG MCP</div>
            <div class="auth-product-subtitle">Upload documents, search them, connect MCP</div>
          </div>
        </div>

        <div class="auth-value-stack">
          <div class="auth-value-item">
            <q-icon name="folder_managed" />
            <span>Create one knowledge base for your private documents.</span>
          </div>
          <div class="auth-value-item">
            <q-icon name="schema" />
            <span>Add files or pasted text and let the backend index them.</span>
          </div>
          <div class="auth-value-item">
            <q-icon name="key" />
            <span>Search in the UI or connect an MCP client with an API key.</span>
          </div>
        </div>
      </div>

      <div class="auth-form-panel">
        <div class="auth-form-head">
          <div class="eyebrow">Start here</div>
          <h1>{{ authMode === 'login' ? 'Sign in' : 'Create workspace' }}</h1>
        </div>

        <q-banner v-if="error" rounded class="feedback-banner feedback-banner-error">
          <template #avatar>
            <q-icon name="error" />
          </template>
          {{ error }}
        </q-banner>

        <q-tabs v-model="authMode" dense active-color="primary" indicator-color="primary">
          <q-tab name="login" label="Sign in" />
          <q-tab name="register" label="Register" />
        </q-tabs>

        <q-form class="auth-form" @submit.prevent="submit">
          <q-input v-model="form.email" label="Email" type="email" outlined dense />
          <q-input v-model="form.password" label="Password" type="password" outlined dense />
          <q-input
            v-if="authMode === 'register'"
            v-model="form.fullName"
            label="Full name"
            outlined
            dense
          />
          <q-btn
            type="submit"
            color="primary"
            icon="login"
            :label="authMode === 'login' ? 'Sign in' : 'Create account'"
            :loading="busy"
            no-caps
          />
        </q-form>
      </div>
    </section>
  </q-page>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';

defineProps<{
  busy: boolean;
  error: string;
}>();

const emit = defineEmits<{
  authenticate: [
    payload: {
      mode: 'login' | 'register';
      email: string;
      password: string;
      full_name?: string | null;
    },
  ];
}>();

const authMode = ref<'login' | 'register'>('login');
const form = reactive({ email: '', password: '', fullName: '' });

function submit() {
  emit('authenticate', {
    mode: authMode.value,
    email: form.email,
    password: form.password,
    full_name: form.fullName || null,
  });
}
</script>
