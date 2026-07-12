(function (global) {
  'use strict';

  class OpenRagAgent {
    static init(options) {
      const widget = new OpenRagAgent(options || {});
      widget.mount();
      return widget;
    }

    constructor({ publicKey, baseUrl, title = 'Knowledge Agent', greeting, position = 'right' }) {
      if (!publicKey) throw new Error('OpenRagAgent: publicKey is required');
      this.publicKey = publicKey;
      this.baseUrl = String(baseUrl || global.location.origin).replace(/\/$/, '');
      this.title = title;
      this.greeting = greeting || 'Hello. Ask me a question about the connected documents.';
      this.position = position === 'left' ? 'left' : 'right';
      this.sessionId = this.getSessionId();
      this.busy = false;
    }

    mount() {
      if (this.host) return this;
      this.host = document.createElement('div');
      this.host.id = `open-rag-agent-${this.publicKey.slice(-8)}`;
      document.body.appendChild(this.host);
      const root = this.host.attachShadow({ mode: 'open' });
      root.innerHTML = this.template();
      this.root = root;
      this.panel = root.querySelector('[data-panel]');
      this.messages = root.querySelector('[data-messages]');
      this.form = root.querySelector('form');
      this.input = root.querySelector('textarea');
      this.sendButton = root.querySelector('[data-send]');
      this.status = root.querySelector('[data-status]');
      root.querySelector('[data-launcher]').addEventListener('click', () => this.toggle(true));
      root.querySelector('[data-close]').addEventListener('click', () => this.toggle(false));
      this.form.addEventListener('submit', (event) => this.submit(event));
      this.input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          this.form.requestSubmit();
        }
      });
      this.addMessage(this.greeting, 'agent');
      return this;
    }

    toggle(open) {
      const shouldOpen = open === undefined ? this.panel.hidden : open;
      this.panel.hidden = !shouldOpen;
      if (shouldOpen) setTimeout(() => this.input.focus(), 0);
    }

    destroy() {
      this.host?.remove();
      this.host = null;
    }

    async submit(event) {
      event.preventDefault();
      const message = this.input.value.trim();
      if (!message || this.busy) return;
      this.addMessage(message, 'user');
      this.input.value = '';
      this.setBusy(true);
      const reply = this.addMessage('', 'agent');
      try {
        for await (const item of this.stream(message)) {
          if (item.event === 'RunContent' && item.data?.content) {
            reply.textContent += String(item.data.content);
            this.scrollToLatest();
          }
          if (item.event === 'error') throw new Error(item.data?.message || 'Agent failed');
        }
        if (!reply.textContent) reply.textContent = 'No response content was returned.';
        this.setStatus('Ready');
      } catch (error) {
        reply.remove();
        this.addMessage(error instanceof Error ? error.message : 'Request failed', 'error');
        this.setStatus('Connection failed', true);
      } finally {
        this.setBusy(false);
      }
    }

    async *stream(message) {
      const response = await fetch(
        `${this.baseUrl}/agent-runtime/public/${encodeURIComponent(this.publicKey)}/runs`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, session_id: this.sessionId }),
        },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `Agent request failed (${response.status})`);
      }
      if (!response.body) throw new Error('Streaming response is unavailable');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';
        for (const block of blocks) {
          const parsed = parseEvent(block);
          if (parsed) yield parsed;
        }
        if (done) break;
      }
      const parsed = parseEvent(buffer);
      if (parsed) yield parsed;
    }

    addMessage(text, role) {
      const element = document.createElement('div');
      element.className = `message ${role}`;
      element.textContent = text;
      this.messages.appendChild(element);
      this.scrollToLatest();
      return element;
    }

    setBusy(busy) {
      this.busy = busy;
      this.sendButton.disabled = busy;
      this.input.disabled = busy;
      this.setStatus(busy ? 'Thinking...' : 'Ready');
      if (!busy) this.input.focus();
    }

    setStatus(text, error = false) {
      this.status.textContent = text;
      this.status.classList.toggle('error', error);
    }

    scrollToLatest() {
      this.messages.scrollTop = this.messages.scrollHeight;
    }

    getSessionId() {
      const key = `open-rag-agent-session:${this.publicKey}`;
      let value = global.localStorage.getItem(key);
      if (!value) {
        value = global.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
        global.localStorage.setItem(key, value);
      }
      return value;
    }

    template() {
      const side = this.position;
      return `<style>${styles(side)}</style>
        <button class="launcher" data-launcher aria-label="Open ${escapeHtml(this.title)} chat">✦</button>
        <section class="panel" data-panel hidden aria-label="${escapeHtml(this.title)} chat">
          <header><div><strong>${escapeHtml(this.title)}</strong><span data-status>Ready</span></div>
            <button class="close" data-close aria-label="Close chat">×</button></header>
          <main data-messages aria-live="polite"></main>
          <form><textarea rows="1" placeholder="Ask a question..." aria-label="Message" required></textarea>
            <button class="send" data-send type="submit" aria-label="Send message">➤</button></form>
        </section>`;
    }
  }

  function parseEvent(block) {
    if (!block.trim()) return null;
    let event = 'message';
    const data = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      if (line.startsWith('data:')) data.push(line.slice(5).trim());
    }
    if (!data.length) return null;
    try { return { event, data: JSON.parse(data.join('\n')) }; }
    catch { return { event, data: data.join('\n') }; }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
  }

  function styles(side) {
    return `*{box-sizing:border-box}button,textarea{font:inherit}.launcher{position:fixed;${side}:22px;bottom:22px;z-index:2147483000;width:56px;height:56px;border:0;border-radius:50%;background:#1d4ed8;color:#fff;box-shadow:0 10px 28px rgba(29,78,216,.3);font-size:25px;cursor:pointer}.panel{position:fixed;${side}:22px;bottom:90px;z-index:2147483000;display:grid;grid-template-rows:auto minmax(0,1fr) auto;width:min(380px,calc(100vw - 28px));height:min(600px,calc(100vh - 120px));overflow:hidden;border:1px solid #d7dee8;border-radius:8px;background:#fff;box-shadow:0 18px 50px rgba(23,32,47,.2);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#17202f}.panel[hidden]{display:none}header{display:flex;align-items:center;justify-content:space-between;padding:15px 16px;border-bottom:1px solid #e3e8ef;background:#fff}header div{display:grid}header strong{font-size:15px}header span{color:#667085;font-size:11px}.error{color:#b42318!important}.close{width:32px;height:32px;border:0;background:transparent;color:#667085;font-size:24px;cursor:pointer}main{display:flex;flex-direction:column;gap:10px;min-height:0;padding:14px;overflow-y:auto;background:#f8fafc}.message{max-width:86%;padding:10px 12px;border:1px solid #dce3ec;border-radius:7px;line-height:1.45;overflow-wrap:anywhere;white-space:pre-wrap;font-size:14px}.message.agent{align-self:flex-start;background:#fff}.message.user{align-self:flex-end;border-color:#1d4ed8;background:#1d4ed8;color:#fff}.message.error{align-self:flex-start;border-color:#fda29b;background:#fff1f0;color:#b42318}form{display:grid;grid-template-columns:minmax(0,1fr) 40px;gap:8px;padding:11px;border-top:1px solid #e3e8ef;background:#fff}textarea{width:100%;min-height:40px;max-height:110px;resize:none;padding:9px 10px;border:1px solid #cfd7e3;border-radius:6px;outline:none}textarea:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12)}.send{height:40px;border:0;border-radius:6px;background:#1d4ed8;color:#fff;cursor:pointer}.send:disabled{opacity:.5}@media(max-width:480px){.launcher{${side}:14px;bottom:14px}.panel{${side}:7px;bottom:80px;width:calc(100vw - 14px);height:calc(100vh - 94px)}}`;
  }

  global.OpenRagAgent = OpenRagAgent;
})(window);
