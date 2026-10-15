document.addEventListener('DOMContentLoaded', () => {
    const launcher = document.getElementById('mindy-launcher');
    if (!launcher) return; // Not authenticated or partial not included

    const $ = (id) => document.getElementById(id);
    const panel = $('mindy-panel');
    const container = $('mindy-container');
    const backdrop = $('mindy-backdrop');
    const form = $('mindy-input-area');
    const input = $('mindy-input');
    const sendBtn = $('mindy-send');
    const messages = $('mindy-messages');
    const typing = $('mindy-typing');
    const jumpBtn = $('mindy-jump');
    const suggestionsEl = $('mindy-suggestions');
    const counter = $('mindy-counter');
    const historyPanel = $('mindy-history-panel');
    const historyList = $('mindy-history-list');
    const avatarTemplate = $('mindy-avatar-template');

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const MAX_CHARS = 1000;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let conversationId = null;
    let isSending = false;
    let viewingOld = false;
    let loading = null;

    // --- Helpers -------------------------------------------------------------
    async function api(url, options = {}) {
        const headers = { 'X-CSRFToken': csrfToken, ...(options.body ? { 'Content-Type': 'application/json' } : {}) };
        const res = await fetch(url, { credentials: 'same-origin', ...options, headers });
        let data = null;
        try { data = await res.json(); } catch (e) { /* non-JSON response */ }
        if (!res.ok) {
            const err = new Error((data && data.error) || 'request_failed');
            err.status = res.status;
            throw err;
        }
        return data;
    }

    function nearBottom() {
        return messages.scrollHeight - messages.scrollTop - messages.clientHeight < 80;
    }

    function scrollToBottom(force = false) {
        if (force || nearBottom()) {
            messages.scrollTo({ top: messages.scrollHeight, behavior: reduceMotion ? 'auto' : 'smooth' });
            jumpBtn.hidden = true;
        } else {
            jumpBtn.hidden = false;
        }
    }

    function clearMessages() {
        messages.querySelectorAll(':scope > :not(#mindy-typing)').forEach((el) => el.remove());
    }

    function addRow(sender, text) {
        const stickToBottom = nearBottom();
        const row = document.createElement('div');
        row.className = `mindy-message-row ${sender === 'user' ? 'mindy-user' : 'mindy-bot'}`;
        if (sender !== 'user') row.appendChild(avatarTemplate.content.firstElementChild.cloneNode(true));

        const bubble = document.createElement('div');
        bubble.className = 'mindy-bubble';
        const who = document.createElement('span');
        who.className = 'mindy-sr-only';
        who.textContent = sender === 'user' ? 'You said: ' : 'Mindy said: ';
        bubble.append(who, document.createTextNode(text)); // textContent only: never HTML
        row.appendChild(bubble);
        messages.insertBefore(row, typing);
        scrollToBottom(stickToBottom || sender === 'user');
        return row;
    }

    function addNote(text, extra) {
        const note = document.createElement('div');
        note.className = 'mindy-system-message';
        note.textContent = text;
        if (extra) note.appendChild(extra);
        messages.insertBefore(note, typing);
        scrollToBottom(true);
        return note;
    }

    function setSuggestions(list) {
        suggestionsEl.replaceChildren();
        (list || []).slice(0, 5).forEach((label) => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'mindy-chip';
            chip.textContent = label;
            chip.addEventListener('click', () => send(label));
            suggestionsEl.appendChild(chip);
        });
        suggestionsEl.hidden = !suggestionsEl.children.length;
    }

    function setTyping(on) {
        typing.hidden = !on;
        if (on) scrollToBottom(true);
    }

    function updateComposer() {
        const len = input.value.length;
        sendBtn.disabled = isSending || !input.value.trim() || viewingOld || !conversationId;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        if (len > MAX_CHARS - 200) {
            counter.hidden = false;
            counter.textContent = `${len} / ${MAX_CHARS}`;
        } else {
            counter.hidden = true;
        }
    }

    function setComposerEnabled(enabled) {
        form.hidden = !enabled;
        if (!enabled) suggestionsEl.hidden = true;
    }

    // --- Conversation lifecycle -------------------------------------------
    function renderConversation(data) {
        conversationId = data.conversation_id;
        viewingOld = false;
        clearMessages();
        data.messages.forEach((m) => addRow(m.sender, m.message));
        setSuggestions(data.suggestions);
        setComposerEnabled(true);
        scrollToBottom(true);
        updateComposer();
    }

    function init() {
        if (loading) return loading;
        loading = api('/mindy/init', { method: 'POST' })
            .then(renderConversation)
            .catch(() => {
                clearMessages();
                const retry = document.createElement('button');
                retry.type = 'button';
                retry.className = 'mindy-link-btn';
                retry.textContent = 'Try again';
                retry.addEventListener('click', () => { loading = null; init(); });
                addNote("I couldn't connect just now. ", retry);
            })
            .finally(() => { loading = null; });
        return loading;
    }

    async function startNew() {
        if (isSending) return;
        try {
            const data = await api('/mindy/new', { method: 'POST' });
            renderConversation(data);
            closeHistory();
            input.focus();
        } catch (e) {
            addNote("Couldn't start a new chat right now. Please try again.");
        }
    }

    async function send(text) {
        text = (text || '').trim();
        if (!text || isSending || viewingOld || !conversationId) return;
        if (text.length > MAX_CHARS) {
            addNote(`That's a little long. Please keep messages under ${MAX_CHARS} characters.`);
            return;
        }
        isSending = true;
        input.value = '';
        updateComposer();
        setSuggestions([]);
        const row = addRow('user', text);
        setTyping(true);
        const started = performance.now();

        try {
            const data = await api('/mindy/message', {
                method: 'POST',
                body: JSON.stringify({ message: text, conversation_id: conversationId }),
            });
            // Keep the typing dots visible for a beat so the reply doesn't "pop".
            const wait = Math.max(0, 350 - (performance.now() - started));
            await new Promise((r) => setTimeout(r, wait));
            setTyping(false);
            addRow('mindy', data.reply);
            setSuggestions(data.suggestions);
        } catch (err) {
            setTyping(false);
            row.classList.add('is-failed');
            if (err.status === 401) {
                addNote('Your session has ended. Please log in again.');
            } else if (err.status === 404 || err.status === 400) {
                // The conversation was ended or deleted elsewhere: start fresh.
                conversationId = null;
                await init();
                input.value = text;
                addNote('That chat had ended, so I started a new one. Press send to try again.');
            } else {
                const retry = document.createElement('button');
                retry.type = 'button';
                retry.className = 'mindy-link-btn';
                retry.textContent = 'Retry';
                retry.addEventListener('click', () => {
                    row.remove();
                    note.remove();
                    send(text);
                });
                const note = addNote("That didn't send. ", retry);
                if (!input.value) input.value = text;
            }
        } finally {
            isSending = false;
            updateComposer();
            if (window.innerWidth > 767) input.focus();
        }
    }

    // --- Panel open/close ----------------------------------------------------
    function openMindy() {
        panel.hidden = false;
        // Force a layout pass so the fade-in transition still runs, without
        // depending on requestAnimationFrame (paused in background tabs).
        void panel.offsetWidth;
        panel.classList.add('is-open');
        backdrop.classList.add('is-open');
        container.classList.add('is-open');
        launcher.setAttribute('aria-expanded', 'true');
        if (!conversationId && !viewingOld) init();
        setTimeout(() => { input.focus(); scrollToBottom(true); }, reduceMotion ? 0 : 200);
    }

    function closeMindy() {
        panel.classList.remove('is-open');
        backdrop.classList.remove('is-open');
        container.classList.remove('is-open');
        launcher.setAttribute('aria-expanded', 'false');
        setTimeout(() => { if (!panel.classList.contains('is-open')) panel.hidden = true; }, reduceMotion ? 0 : 250);
        launcher.focus();
    }

    launcher.addEventListener('click', () => (panel.classList.contains('is-open') ? closeMindy() : openMindy()));
    // Sidebar / mobile-nav "Mindy" items open the same panel.
    document.querySelectorAll('[data-open-mindy]').forEach((btn) => {
        btn.setAttribute('aria-controls', 'mindy-panel');
        btn.addEventListener('click', openMindy);
    });
    $('mindy-close').addEventListener('click', closeMindy);
    backdrop.addEventListener('click', closeMindy);
    $('mindy-new-btn').addEventListener('click', startNew);
    jumpBtn.addEventListener('click', () => scrollToBottom(true));
    messages.addEventListener('scroll', () => { if (nearBottom()) jumpBtn.hidden = true; });

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape' || !panel.classList.contains('is-open')) return;
        if (!historyPanel.hidden) closeHistory();
        else closeMindy();
    });

    form.addEventListener('submit', (e) => { e.preventDefault(); send(input.value); });
    input.addEventListener('input', updateComposer);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
            e.preventDefault();
            send(input.value);
        }
    });

    // --- History -------------------------------------------------------------
    function openHistory() {
        historyPanel.hidden = false;
        $('mindy-history-close').focus();
        loadHistory();
    }
    function closeHistory() {
        historyPanel.hidden = true;
    }
    $('mindy-history-btn').addEventListener('click', openHistory);
    $('mindy-history-close').addEventListener('click', closeHistory);

    function historyMessage(text) {
        const p = document.createElement('p');
        p.className = 'mindy-history-empty';
        p.textContent = text;
        historyList.replaceChildren(p);
    }

    async function loadHistory() {
        historyMessage('Loading…');
        try {
            const data = await api('/mindy/history');
            if (!data.history.length) {
                historyMessage("No saved conversations yet. Start a new chat and your current one will be saved here.");
                return;
            }
            historyList.replaceChildren();
            data.history.forEach((item) => {
                const card = document.createElement('article');
                card.className = 'mindy-history-item';

                const open = document.createElement('button');
                open.type = 'button';
                open.className = 'mindy-history-open';
                const title = document.createElement('h3');
                title.textContent = item.title;
                const preview = document.createElement('p');
                preview.textContent = item.preview;
                const meta = document.createElement('span');
                meta.className = 'mindy-history-meta';
                meta.textContent = `${item.date} · ${item.time} · ${item.message_count} messages`;
                open.append(title, preview, meta);
                open.addEventListener('click', () => loadConversation(item.id));

                const actions = document.createElement('div');
                actions.className = 'mindy-history-item-actions';
                const rename = document.createElement('button');
                rename.type = 'button';
                rename.textContent = 'Rename';
                rename.addEventListener('click', () => renameConversation(item.id, item.title));
                const del = document.createElement('button');
                del.type = 'button';
                del.textContent = 'Delete';
                del.addEventListener('click', () => deleteConversation(item.id));
                actions.append(rename, del);

                card.append(open, actions);
                historyList.appendChild(card);
            });
        } catch (e) {
            historyMessage("Couldn't load your conversations. Please try again.");
        }
    }

    async function loadConversation(id) {
        try {
            const data = await api(`/mindy/conversation/${id}`);
            clearMessages();
            addNote(`Saved conversation · ${data.title}`);
            data.messages.forEach((m) => addRow(m.sender, m.message));
            viewingOld = true;
            conversationId = null;
            setComposerEnabled(false);
            const back = document.createElement('button');
            back.type = 'button';
            back.className = 'mindy-link-btn';
            back.textContent = 'Back to current chat';
            back.addEventListener('click', () => { viewingOld = false; init(); });
            addNote('This conversation is read-only. ', back);
            closeHistory();
        } catch (e) {
            historyMessage("Couldn't open that conversation.");
        }
    }

    async function renameConversation(id, current) {
        const title = window.prompt('Rename conversation', current);
        if (!title || !title.trim()) return;
        try {
            await api(`/mindy/conversation/${id}/title`, { method: 'PUT', body: JSON.stringify({ title: title.trim().slice(0, 100) }) });
        } catch (e) { /* list reload below shows the unchanged title */ }
        loadHistory();
    }

    async function deleteConversation(id) {
        if (!window.confirm('Delete this conversation? This permanently removes it.')) return;
        try {
            await api(`/mindy/conversation/${id}`, { method: 'DELETE' });
        } catch (e) { /* ignore; list reload shows current state */ }
        loadHistory();
    }

    updateComposer();
});
