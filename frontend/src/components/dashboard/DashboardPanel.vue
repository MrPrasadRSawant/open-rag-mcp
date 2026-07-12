<template>
  <div class="screen-stack">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">Dashboard</div>
        <h1>System overview</h1>
        <p>Analytical summary of groups, documents, processing jobs, and API access.</p>
      </div>
      <div class="screen-actions">
        <q-btn
          flat
          icon="refresh"
          label="Refresh"
          no-caps
          :loading="loading"
          @click="$emit('refresh')"
        />
      </div>
    </section>

    <section class="stat-grid">
      <overview-stat label="Document groups" :value="groupsCount" icon="folder_open" tone="blue" />
      <overview-stat label="Documents" :value="documentsCount" icon="description" tone="slate" />
      <overview-stat label="Indexed chunks" :value="totalChunks" icon="scatter_plot" tone="green" />
      <overview-stat label="Active jobs" :value="activeJobs" icon="pending_actions" tone="amber" />
    </section>

    <section class="content-grid">
      <div class="workspace-panel">
        <div class="panel-heading">
          <div>
            <h2>Current group</h2>
            <p>Documents and search use this selected group.</p>
          </div>
          <q-icon name="folder" />
        </div>
        <div class="dashboard-current-group">
          <strong>{{ selectedGroupName || 'No group selected' }}</strong>
          <span>{{ documentsCount }} documents - {{ totalChunks }} chunks</span>
        </div>
        <div class="panel-actions">
          <q-btn
            color="primary"
            icon="folder_open"
            label="Manage groups"
            no-caps
            :to="{ name: 'groups' }"
          />
          <q-btn
            flat
            icon="description"
            label="Open documents"
            no-caps
            :to="{ name: 'documents' }"
          />
        </div>
      </div>

      <div class="workspace-panel">
        <div class="panel-heading">
          <div>
            <h2>Process status</h2>
            <p>Recent ingestion activity.</p>
          </div>
          <q-badge outline color="primary">{{ activeJobs }} active</q-badge>
        </div>
        <q-list v-if="jobs.length" separator class="flush-list">
          <q-item v-for="job in jobs" :key="job.id">
            <q-item-section avatar>
              <q-icon :name="job.status === 'completed' ? 'task_alt' : 'pending_actions'" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ job.status }}</q-item-label>
              <q-item-label caption>{{ job.job_type }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="empty-state compact">
          <q-icon name="pending_actions" />
          <span>No processing jobs yet.</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { ProcessingJob } from '@/services/api';
import OverviewStat from '@/components/workspace/OverviewStat.vue';

defineProps<{
  groupsCount: number;
  documentsCount: number;
  totalChunks: number;
  activeJobs: number;
  selectedGroupName: string;
  jobs: ProcessingJob[];
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
}>();
</script>
