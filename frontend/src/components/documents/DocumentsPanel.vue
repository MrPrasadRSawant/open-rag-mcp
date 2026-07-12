<template>
  <div class="screen-stack">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">Documents</div>
        <h1>Manage documents</h1>
        <p>Choose a document group, then add, edit, delete, and monitor documents in that group.</p>
      </div>
    </section>

    <section class="workspace-panel document-toolbar">
      <q-select
        v-model="currentGroupId"
        :options="groupOptions"
        emit-value
        map-options
        label="Document group"
        outlined
        dense
        class="toolbar-select"
      />
      <q-btn
        color="primary"
        icon="add"
        label="Add document"
        :disable="!selectedGroupId"
        no-caps
        @click="openCreateDialog"
      />
    </section>

    <q-banner v-if="!selectedGroupId" rounded class="feedback-banner feedback-banner-error">
      <template #avatar>
        <q-icon name="folder_off" />
      </template>
      Select a document group before creating documents.
      <template #action>
        <q-btn flat dense icon="folder_open" label="Groups" no-caps :to="{ name: 'groups' }" />
      </template>
    </q-banner>

    <section class="workspace-panel table-panel">
      <div class="panel-heading table-heading">
        <div>
          <h2>Document list</h2>
          <p>{{ documents.length }} records in the selected group</p>
        </div>
        <q-btn flat dense icon="refresh" aria-label="Refresh documents" @click="$emit('refresh')" />
      </div>
      <q-table
        flat
        :rows="documents"
        :columns="documentColumns"
        row-key="id"
        :pagination="{ rowsPerPage: 8 }"
      >
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-chip dense square :color="statusColor(props.row.status)" text-color="white">
              {{ props.row.status }}
            </q-chip>
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <div class="row-actions">
              <q-btn flat dense round icon="edit" @click="startEdit(props.row)">
                <q-tooltip>Edit document title</q-tooltip>
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
                <q-tooltip>Delete document</q-tooltip>
              </q-btn>
            </div>
          </q-td>
        </template>
      </q-table>
    </section>

    <q-dialog v-model="createDialogOpen">
      <q-card class="document-dialog">
        <q-card-section>
          <div class="text-h6">Add document</div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="dialog-form">
            <q-select
              v-model="createMode"
              :options="createModeOptions"
              emit-value
              map-options
              label="Document type"
              outlined
              dense
            />

            <template v-if="createMode === 'text'">
              <q-input v-model="textForm.title" label="Title" outlined dense />
              <q-input v-model="textForm.text" label="Text" type="textarea" outlined autogrow />
            </template>

            <template v-else>
              <q-input v-model="uploadTitle" label="Title" outlined dense />
              <q-file v-model="uploadFile" label="File" outlined dense clearable>
                <template #prepend>
                  <q-icon name="upload_file" />
                </template>
              </q-file>
            </template>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Cancel" no-caps v-close-popup />
            <q-btn
              type="submit"
              color="primary"
              icon="add"
              label="Create record"
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
          <div class="text-h6">Edit document</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="editTitle" label="Title" outlined dense autofocus />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" no-caps v-close-popup />
          <q-btn color="primary" label="Save" no-caps @click="submitEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="edit-dialog">
        <q-card-section>
          <div class="text-h6">Delete document</div>
        </q-card-section>
        <q-card-section class="dialog-form">
          <p class="confirm-copy">
            Delete <strong>{{ deleteTarget?.title }}</strong
            >? This will remove the document and its indexed search data.
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

import type { DocumentItem } from '@/services/api';
import type { GroupOption } from '@/types/workspace';

const props = defineProps<{
  groupOptions: GroupOption[];
  selectedGroupId: string | null;
  documents: DocumentItem[];
  busy: boolean;
}>();

const emit = defineEmits<{
  selectGroup: [groupId: string];
  queueText: [payload: { title: string; text: string }];
  queueUpload: [payload: { title?: string; file: File }];
  updateDocument: [documentId: string, payload: { title?: string }];
  deleteDocument: [documentId: string];
  refresh: [];
}>();

const currentGroupId = computed({
  get: () => props.selectedGroupId,
  set: (value) => {
    if (value) emit('selectGroup', value);
  },
});

const createMode = ref<'text' | 'upload'>('text');
const createDialogOpen = ref(false);
const textForm = reactive({ title: '', text: '' });
const uploadTitle = ref('');
const uploadFile = ref<File | null>(null);
const editDialogOpen = ref(false);
const editDocumentId = ref('');
const editTitle = ref('');
const deleteDialogOpen = ref(false);
const deleteTarget = ref<DocumentItem | null>(null);

const createModeOptions = [
  { label: 'Text', value: 'text' },
  { label: 'Upload file', value: 'upload' },
];

const documentColumns: QTableColumn<DocumentItem>[] = [
  { name: 'title', label: 'Title', field: 'title', align: 'left', sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'left', sortable: true },
  { name: 'chunks', label: 'Chunks', field: 'chunk_count', align: 'right', sortable: true },
  { name: 'source', label: 'Source', field: (row) => row.source_name || 'text', align: 'left' },
  { name: 'updated', label: 'Updated', field: 'updated_at', align: 'left', sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' },
];

function openCreateDialog() {
  createMode.value = 'text';
  textForm.title = '';
  textForm.text = '';
  uploadTitle.value = '';
  uploadFile.value = null;
  createDialogOpen.value = true;
}

function submitCreate() {
  if (createMode.value === 'text') {
    if (!textForm.title.trim() || !textForm.text.trim()) return;
    emit('queueText', { title: textForm.title, text: textForm.text });
  } else {
    if (!uploadFile.value) return;
    const payload: { title?: string; file: File } = { file: uploadFile.value };
    if (uploadTitle.value) {
      payload.title = uploadTitle.value;
    }
    emit('queueUpload', payload);
  }
  createDialogOpen.value = false;
}

function statusColor(status: string) {
  if (status === 'completed') return 'positive';
  if (status === 'failed') return 'negative';
  if (status === 'processing') return 'warning';
  return 'blue-grey';
}

function startEdit(document: DocumentItem) {
  editDocumentId.value = document.id;
  editTitle.value = document.title;
  editDialogOpen.value = true;
}

function submitEdit() {
  if (!editDocumentId.value || !editTitle.value.trim()) return;
  emit('updateDocument', editDocumentId.value, { title: editTitle.value });
  editDialogOpen.value = false;
}

function openDeleteDialog(document: DocumentItem) {
  deleteTarget.value = document;
  deleteDialogOpen.value = true;
}

function confirmDelete() {
  if (!deleteTarget.value) return;
  emit('deleteDocument', deleteTarget.value.id);
  deleteDialogOpen.value = false;
  deleteTarget.value = null;
}
</script>
