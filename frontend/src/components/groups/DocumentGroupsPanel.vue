<template>
  <div class="screen-stack">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">Document Groups</div>
        <h1>Manage document groups</h1>
        <p>
          Groups separate document collections. Select one before working with documents or search.
        </p>
      </div>
    </section>

    <section class="workspace-panel document-toolbar">
      <q-select
        v-model="currentGroupId"
        :options="groupOptions"
        emit-value
        map-options
        label="Selected document group"
        outlined
        dense
        class="toolbar-select"
        :disable="!groups.length"
      />
      <q-btn color="primary" icon="add" label="Add new group" no-caps @click="openCreateDialog" />
    </section>

    <section class="workspace-panel table-panel">
      <div class="panel-heading table-heading">
        <div>
          <h2>Groups list</h2>
          <p>{{ groups.length }} groups available</p>
        </div>
        <q-btn flat dense icon="refresh" aria-label="Refresh groups" @click="$emit('refresh')" />
      </div>
      <q-table flat :rows="groups" :columns="columns" row-key="id" :pagination="{ rowsPerPage: 8 }">
        <template #body-cell-active="props">
          <q-td :props="props">
            <q-chip
              v-if="selectedGroupId === props.row.id"
              dense
              square
              color="primary"
              text-color="white"
            >
              Selected
            </q-chip>
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <div class="row-actions">
              <q-btn
                flat
                dense
                round
                icon="check_circle"
                @click="$emit('selectGroup', props.row.id)"
              >
                <q-tooltip>Select group</q-tooltip>
              </q-btn>
              <q-btn flat dense round icon="edit" @click="openEditDialog(props.row)">
                <q-tooltip>Edit group</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                round
                color="negative"
                icon="delete"
                :disable="busy"
                @click="openDeleteDialog(props.row)"
              >
                <q-tooltip>Delete group</q-tooltip>
              </q-btn>
            </div>
          </q-td>
        </template>
      </q-table>
    </section>

    <q-dialog v-model="createDialogOpen">
      <q-card class="edit-dialog">
        <q-card-section>
          <div class="text-h6">Create document group</div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="dialog-form">
            <q-input v-model="createForm.name" label="Group name" outlined dense autofocus />
            <q-input v-model="createForm.description" label="Description" outlined dense />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Cancel" no-caps v-close-popup />
            <q-btn
              type="submit"
              color="primary"
              icon="add"
              label="Create"
              :loading="busy"
              no-caps
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog v-model="editDialogOpen">
      <q-card class="edit-dialog">
        <q-card-section>
          <div class="text-h6">Edit document group</div>
        </q-card-section>
        <q-form @submit.prevent="submitEdit">
          <q-card-section class="dialog-form">
            <q-input v-model="editForm.name" label="Group name" outlined dense autofocus />
            <q-input v-model="editForm.description" label="Description" outlined dense />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Cancel" no-caps v-close-popup />
            <q-btn type="submit" color="primary" icon="save" label="Save" :loading="busy" no-caps />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="edit-dialog">
        <q-card-section>
          <div class="text-h6">Delete document group</div>
        </q-card-section>
        <q-card-section class="dialog-form">
          <p class="confirm-copy">
            Delete <strong>{{ deleteTarget?.name }}</strong
            >? This will remove the group, its documents, API keys, and indexed search data.
          </p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" no-caps :disable="busy" @click="deleteDialogOpen = false" />
          <q-btn
            color="negative"
            icon="delete"
            label="Delete"
            :loading="busy"
            no-caps
            @click="confirmDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import type { QTableColumn } from 'quasar';
import { computed, reactive, ref } from 'vue';

import type { DocumentGroup } from '@/services/api';

const props = defineProps<{
  groups: DocumentGroup[];
  selectedGroupId: string | null;
  busy: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
  selectGroup: [groupId: string];
  createGroup: [payload: { name: string; description?: string | null }];
  updateGroup: [groupId: string, payload: { name?: string; description?: string | null }];
  deleteGroup: [groupId: string];
}>();

const createDialogOpen = ref(false);
const editDialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const editingGroup = ref<DocumentGroup | null>(null);
const deleteTarget = ref<DocumentGroup | null>(null);
const createForm = reactive({ name: '', description: '' });
const editForm = reactive({ name: '', description: '' });

const groupOptions = computed(() =>
  props.groups.map((group) => ({ label: group.name, value: group.id })),
);
const currentGroupId = computed({
  get: () => props.selectedGroupId,
  set: (value) => {
    if (value) emit('selectGroup', value);
  },
});

const columns: QTableColumn<DocumentGroup>[] = [
  { name: 'active', label: '', field: 'id', align: 'left' },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  {
    name: 'description',
    label: 'Description',
    field: (row) => row.description || '',
    align: 'left',
  },
  { name: 'updated', label: 'Updated', field: 'updated_at', align: 'left', sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' },
];

function openCreateDialog() {
  createForm.name = '';
  createForm.description = '';
  createDialogOpen.value = true;
}

function submitCreate() {
  if (!createForm.name.trim()) return;
  emit('createGroup', {
    name: createForm.name,
    description: createForm.description || null,
  });
  createDialogOpen.value = false;
}

function openEditDialog(group: DocumentGroup) {
  editingGroup.value = group;
  editForm.name = group.name;
  editForm.description = group.description || '';
  editDialogOpen.value = true;
}

function submitEdit() {
  if (!editingGroup.value || !editForm.name.trim()) return;
  emit('updateGroup', editingGroup.value.id, {
    name: editForm.name,
    description: editForm.description || null,
  });
  editDialogOpen.value = false;
}

function openDeleteDialog(group: DocumentGroup) {
  deleteTarget.value = group;
  deleteDialogOpen.value = true;
}

function confirmDelete() {
  if (!deleteTarget.value) return;
  emit('deleteGroup', deleteTarget.value.id);
  deleteDialogOpen.value = false;
  deleteTarget.value = null;
}
</script>
