<template>
  <div class="screen-stack documentation-screen">
    <section class="screen-hero">
      <div>
        <div class="eyebrow">Documentation</div>
        <h1>Product documentation</h1>
        <p>Browse functional and technical documentation from the project docs folder.</p>
      </div>
      <q-btn flat round icon="refresh" :loading="loading" @click="loadCatalog">
        <q-tooltip>Refresh documentation</q-tooltip>
      </q-btn>
    </section>

    <section class="workspace-panel documentation-tabs-panel">
      <q-tabs v-model="activeCategory" dense align="left" narrow-indicator>
        <q-tab name="functional" icon="fact_check" label="Functional" no-caps />
        <q-tab name="technical" icon="code" label="Technical" no-caps />
      </q-tabs>
    </section>

    <section class="documentation-layout">
      <aside class="workspace-panel documentation-index">
        <div class="panel-heading">
          <div>
            <h2>{{ activeCategoryLabel }}</h2>
            <p>{{ activePages.length }} pages</p>
          </div>
        </div>

        <q-list v-if="activePages.length" class="doc-page-list" separator>
          <q-item
            v-for="page in activePages"
            :key="page.slug"
            clickable
            :active="page.slug === activeSlug"
            active-class="selected-list-item"
            @click="activeSlug = page.slug"
          >
            <q-item-section>
              <q-item-label lines="2">{{ page.title }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="empty-state compact">
          <q-icon name="article" />
          <span>No documentation pages found.</span>
        </div>
      </aside>

      <article class="workspace-panel documentation-reader">
        <div v-if="loading" class="empty-state">
          <q-spinner size="24px" />
          <span>Loading documentation...</span>
        </div>
        <div v-else-if="error" class="empty-state">
          <q-icon name="error_outline" color="negative" />
          <span>{{ error }}</span>
        </div>
        <div
          v-else-if="activePage"
          ref="reader"
          class="markdown-doc"
          v-html="renderedHtml"
          @click="handleDocClick"
        ></div>
        <div v-else class="empty-state">
          <q-icon name="description" />
          <span>Select a documentation page.</span>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { computed, nextTick, onMounted, ref, watch } from 'vue';

import {
  getDocumentation,
  type DocumentationCatalog,
  type DocumentationPage,
} from '@/services/api';

type MermaidApi = {
  initialize: (config: Record<string, unknown>) => void;
  run: (config: { nodes: HTMLElement[] }) => Promise<void>;
};

declare global {
  interface Window {
    mermaid?: MermaidApi;
  }
}

const MERMAID_SCRIPT_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';

const props = defineProps<{
  token: string;
}>();
const emit = defineEmits<{
  error: [message: string];
}>();

const catalog = ref<DocumentationCatalog>({ categories: [] });
const activeCategory = ref('functional');
const activeSlug = ref<string | null>(null);
const loading = ref(false);
const error = ref('');
const reader = ref<HTMLElement | null>(null);
let mermaidScriptPromise: Promise<void> | null = null;

marked.setOptions({ breaks: true, gfm: true });

const activeCategoryData = computed(() =>
  catalog.value.categories.find((category) => category.key === activeCategory.value),
);
const activeCategoryLabel = computed(() => activeCategoryData.value?.label || 'Documentation');
const activePages = computed<DocumentationPage[]>(() => activeCategoryData.value?.pages || []);
const activePage = computed(
  () => activePages.value.find((page) => page.slug === activeSlug.value) || activePages.value[0],
);
const renderedHtml = computed(() => {
  if (!activePage.value) return '';
  return DOMPurify.sanitize(marked.parse(activePage.value.content) as string, {
    ADD_ATTR: ['target'],
  });
});

onMounted(loadCatalog);

watch(activeCategory, () => {
  activeSlug.value = activePages.value[0]?.slug || null;
});

watch(
  activePage,
  async (page) => {
    if (page) activeSlug.value = page.slug;
    await renderMermaid();
  },
  { flush: 'post' },
);

watch(renderedHtml, renderMermaid, { flush: 'post' });

async function loadCatalog() {
  if (!props.token) return;
  loading.value = true;
  error.value = '';
  try {
    catalog.value = await getDocumentation(props.token);
    activeSlug.value = activePages.value[0]?.slug || null;
  } catch (requestError) {
    error.value =
      requestError instanceof Error ? requestError.message : 'Unable to load documentation.';
    emit('error', error.value);
  } finally {
    loading.value = false;
    await renderMermaid();
  }
}

async function handleDocClick(event: MouseEvent) {
  const target = event.target instanceof Element ? event.target.closest('a') : null;
  if (!(target instanceof HTMLAnchorElement)) return;

  const link = target.dataset.docSlug
    ? {
        category: target.dataset.docCategory || activeCategory.value,
        slug: target.dataset.docSlug,
        hash: target.dataset.docHash || null,
      }
    : parseDocumentationLink(target.getAttribute('href') || '');
  if (!link || !hasPage(link.category, link.slug)) return;

  event.preventDefault();
  await selectDocumentationPage(link.category, link.slug, link.hash);
}

function parseDocumentationLink(href: string) {
  const decodedHref = decodeURIComponent(href).replace(/\\/g, '/');
  const [pathWithQuery = '', hash] = decodedHref.split('#', 2);
  const cleanPath = pathWithQuery.split('?', 1)[0] || '';
  if (!cleanPath.endsWith('.md')) return null;

  const slug = cleanPath.split('/').pop()?.replace(/\.md$/, '');
  if (!slug) return null;

  let category = activeCategory.value;
  if (cleanPath.includes('technical_docs/')) category = 'technical';
  if (cleanPath.includes('functional_docs/')) category = 'functional';

  return { category, slug, hash: hash || null };
}

function hasPage(category: string, slug: string) {
  return Boolean(
    catalog.value.categories
      .find((item) => item.key === category)
      ?.pages.some((page) => page.slug === slug),
  );
}

async function selectDocumentationPage(category: string, slug: string, hash: string | null) {
  activeCategory.value = category;
  await nextTick();
  activeSlug.value = slug;
  await nextTick();
  await renderMermaid();
  if (hash) {
    reader.value?.querySelector(`#${CSS.escape(hash)}`)?.scrollIntoView({ block: 'start' });
  }
}

async function renderMermaid() {
  await nextTick();
  if (!reader.value) return;
  enhanceDocumentationLinks();

  const mermaidBlocks = Array.from(
    reader.value.querySelectorAll<HTMLElement>('pre > code.language-mermaid'),
  );
  if (!mermaidBlocks.length) return;

  const nodes = mermaidBlocks.map((block, index) => {
    const pre = block.parentElement as HTMLElement;
    const container = document.createElement('div');
    container.className = 'mermaid';
    container.id = `doc-mermaid-${activeCategory.value}-${activeSlug.value || 'page'}-${index}`;
    container.textContent = block.textContent || '';
    pre.replaceWith(container);
    return container;
  });

  try {
    await loadMermaid();
    window.mermaid?.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'default',
    });
    await window.mermaid?.run({ nodes });
  } catch {
    nodes.forEach((node) => {
      const fallback = document.createElement('pre');
      fallback.className = 'mermaid-fallback';
      fallback.textContent = node.textContent || '';
      node.replaceWith(fallback);
    });
  }
}

function enhanceDocumentationLinks() {
  if (!reader.value) return;

  reader.value.querySelectorAll<HTMLAnchorElement>('a[href]').forEach((anchor) => {
    const link = parseDocumentationLink(anchor.getAttribute('href') || '');
    if (!link) return;

    const page = findPage(link.category, link.slug);
    if (!page) return;

    anchor.dataset.docCategory = link.category;
    anchor.dataset.docSlug = link.slug;
    if (link.hash) anchor.dataset.docHash = link.hash;
    else delete anchor.dataset.docHash;
    anchor.href = '#';
    anchor.title = `Open ${page.title}`;
    anchor.classList.add('doc-internal-link');
  });
}

function findPage(category: string, slug: string) {
  return catalog.value.categories
    .find((item) => item.key === category)
    ?.pages.find((page) => page.slug === slug);
}

function loadMermaid() {
  if (window.mermaid) return Promise.resolve();
  mermaidScriptPromise ||= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = MERMAID_SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Unable to load Mermaid renderer.'));
    document.head.appendChild(script);
  });
  return mermaidScriptPromise;
}
</script>
