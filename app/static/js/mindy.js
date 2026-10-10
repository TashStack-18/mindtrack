document.addEventListener('DOMContentLoaded', () => {
    const launcher = document.getElementById('mindy-launcher');
    if (!launcher) return; // Not authenticated or partial not included

    const panel = document.getElementById('mindy-panel');
    const closeBtn = document.getElementById('mindy-close');
    const backdrop = document.getElementById('mindy-backdrop');
    const container = document.getElementById('mindy-container');
    
    const inputArea = document.getElementById('mindy-input-area');
    const input = document.getElementById('mindy-input');
    const sendBtn = document.getElementById('mindy-send');
    const messagesContainer = document.getElementById('mindy-messages');
    const typingIndicator = document.getElementById('mindy-typing');
    
    // Avatar template - wait, it was hardcoded originally but we can build the DOM
    
    const historyBtn = document.getElementById('mindy-history-btn');
    const historyPanel = document.getElementById('mindy-history-panel');
    const historyClose = document.getElementById('mindy-history-close');
    const historyList = document.getElementById('mindy-history-list');
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    let mindyState = {
        turn: 0,
        last_intents: [],
        last_templates: [],
        context_used_turn: -99
    };
    
    let isWaitingForReply = false;
    let currentConversationId = null;
    let isReopenedOld = false;

    // --- Avatar SVG Factory ---
    function createMindyAvatar() {
        const div = document.createElement('div');
        div.className = 'mindy-avatar-small';
        div.innerHTML = `<img src="/static/img/mindy-full.svg" alt="Mindy Avatar" style="width: 100%; height: 100%; object-fit: contain;">`;
        return div;
    }

    // --- Initializer ---
    async function initMindySession() {
        if (isReopenedOld) {
            // Already viewing an old session, don't re-init automatically unless we closed and opened?
            // "But a completely new Mindy session must start with a clean context."
            // We will just do a standard start.
            clearMessages();
            isReopenedOld = false;
        }
        
        try {
            const response = await fetch('/mindy/init', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken }
            });
            const data = await response.json();
            
            if (data.conversation_id) {
                currentConversationId = data.conversation_id;
                mindyState = data.state;
                
                clearMessages();
                data.messages.forEach(msg => {
                    if (msg.sender === 'user') {
                        appendUserMessage(msg.message, false);
                    } else {
                        appendBotMessage(msg.message, false);
                    }
                });
                scrollToBottom();
                
                // Show controls
                inputArea.style.display = 'flex';
            }
        } catch (e) {
            console.error("Init Mindy Error:", e);
        }
    }

    // --- UI Toggles ---
    function openMindy() {
        panel.classList.add('is-open');
        backdrop.classList.add('is-open');
        container.classList.add('is-open');
        launcher.setAttribute('aria-expanded', 'true');
        
        if (!currentConversationId && !isReopenedOld) {
            initMindySession();
        }
        
        setTimeout(() => {
            if (!isReopenedOld) input.focus();
            scrollToBottom();
        }, 300);
    }

    function closeMindy() {
        panel.classList.remove('is-open');
        backdrop.classList.remove('is-open');
        container.classList.remove('is-open');
        launcher.setAttribute('aria-expanded', 'false');
    }

    launcher.addEventListener('click', openMindy);
    closeBtn.addEventListener('click', closeMindy);
    backdrop.addEventListener('click', () => {
        if (historyPanel.style.display === 'flex') {
            closeHistory();
        } else {
            closeMindy();
        }
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (historyPanel.style.display === 'flex') {
                closeHistory();
            } else if (panel.classList.contains('is-open')) {
                closeMindy();
            }
        }
    });

    // --- Messaging ---
    function clearMessages() {
        const msgs = messagesContainer.querySelectorAll('.mindy-message-row:not(#mindy-typing)');
        msgs.forEach(m => m.remove());
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function appendUserMessage(text, scroll=true) {
        const row = document.createElement('div');
        row.className = 'mindy-message-row mindy-user';
        
        const bubble = document.createElement('div');
        bubble.className = 'mindy-bubble';
        bubble.textContent = text;
        
        row.appendChild(bubble);
        messagesContainer.insertBefore(row, typingIndicator);
        if (scroll) scrollToBottom();
    }

    function appendBotMessage(text, scroll=true) {
        const row = document.createElement('div');
        row.className = 'mindy-message-row mindy-bot';
        
        row.appendChild(createMindyAvatar());
        
        const bubble = document.createElement('div');
        bubble.className = 'mindy-bubble';
        
        const sr = document.createElement('span');
        sr.className = 'mindy-sr-only';
        sr.textContent = 'Mindy said: ';
        
        const textNode = document.createTextNode(text);
        bubble.appendChild(sr);
        bubble.appendChild(textNode);
        row.appendChild(bubble);
        
        messagesContainer.insertBefore(row, typingIndicator);
        if (scroll) scrollToBottom();
    }

    function appendSystemMessage(text) {
        const row = document.createElement('div');
        row.className = 'mindy-system-message';
        row.textContent = text;
        messagesContainer.insertBefore(row, typingIndicator);
        scrollToBottom();
    }

    async function sendMessage() {
        if (isReopenedOld) return; // Cannot send in old
        const text = input.value.trim();
        if (!text || isWaitingForReply || !currentConversationId) return;

        input.value = '';
        input.style.height = 'auto';
        sendBtn.setAttribute('disabled', 'true');
        isWaitingForReply = true;
        
        appendUserMessage(text);
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const response = await fetch('/mindy/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    message: text,
                    state: mindyState,
                    conversation_id: currentConversationId
                })
            });

            if (!response.ok) throw new Error('Network error');

            const data = await response.json();
            mindyState = data.state;
            
            const delay = Math.min(Math.max(data.reply.length * 20, 800), 2000);
            setTimeout(() => {
                typingIndicator.style.display = 'none';
                appendBotMessage(data.reply);
                isWaitingForReply = false;
                
                if (input.value.trim().length > 0) sendBtn.removeAttribute('disabled');
                if (window.innerWidth > 767) input.focus();
            }, delay);

        } catch (error) {
            typingIndicator.style.display = 'none';
            appendBotMessage("I'm having trouble connecting right now. Let's try again in a moment.");
            isWaitingForReply = false;
            if (input.value.trim() === '') {
                input.value = text;
                sendBtn.removeAttribute('disabled');
            }
        }
    }

    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = (input.scrollHeight < 120 ? input.scrollHeight : 120) + 'px';
        if (input.value.trim().length > 0 && !isWaitingForReply) {
            sendBtn.removeAttribute('disabled');
        } else {
            sendBtn.setAttribute('disabled', 'true');
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);



    // --- History ---
    function openHistory() {
        historyPanel.style.display = 'flex';
        loadHistory();
    }
    function closeHistory() {
        historyPanel.style.display = 'none';
    }
    
    if (historyBtn) {
        historyBtn.addEventListener('click', openHistory);
    }
    historyClose.addEventListener('click', closeHistory);
    
    async function loadHistory() {
        historyList.innerHTML = '<div style="text-align:center; padding: 20px; color:var(--mindy-subtext);">Loading...</div>';
        try {
            const res = await fetch('/mindy/history');
            const data = await res.json();
            
            if (data.history.length === 0) {
                historyList.innerHTML = '<div style="text-align:center; padding: 20px; color:var(--mindy-subtext);">No saved conversations yet.</div>';
                return;
            }
            
            historyList.innerHTML = '';
            data.history.forEach(item => {
                const el = document.createElement('div');
                el.className = 'mindy-history-item';
                el.innerHTML = `
                    <h3>${item.title.replace(/</g, "&lt;")}</h3>
                    <p>${item.preview.replace(/</g, "&lt;")}</p>
                    <div class="mindy-history-item-meta">
                        <span>${item.date} at ${item.time} &middot; ${item.message_count} msgs</span>
                        <div class="mindy-history-item-actions">
                            <button onclick="window.renameMindyConv(${item.id})">Rename</button>
                            <button onclick="window.deleteMindyConv(${item.id})">Delete</button>
                        </div>
                    </div>
                `;
                el.addEventListener('click', (e) => {
                    if (e.target.tagName !== 'BUTTON') {
                        loadConversation(item.id);
                        closeHistory();
                    }
                });
                historyList.appendChild(el);
            });
        } catch(e) {
            historyList.innerHTML = '<div style="text-align:center; padding: 20px; color:var(--mindy-subtext);">Failed to load history.</div>';
        }
    }
    
    async function loadConversation(id) {
        try {
            const res = await fetch(`/mindy/conversation/${id}`);
            const data = await res.json();
            
            clearMessages();
            data.messages.forEach(msg => {
                if (msg.sender === 'user') appendUserMessage(msg.message, false);
                else appendBotMessage(msg.message, false);
            });
            scrollToBottom();
            
            isReopenedOld = true;
            currentConversationId = null;
            inputArea.style.display = 'none';
            
            appendSystemMessage(`Saved conversation: ${data.title}`);
            
            // Add button to start new
            const newBtnContainer = document.createElement('div');
            newBtnContainer.style.textAlign = 'center';
            newBtnContainer.style.marginTop = '16px';
            const newBtn = document.createElement('button');
            newBtn.className = 'mindy-btn-primary';
            newBtn.textContent = 'Start New Check-in';
            newBtn.onclick = () => {
                isReopenedOld = false;
                initMindySession();
            };
            newBtnContainer.appendChild(newBtn);
            messagesContainer.insertBefore(newBtnContainer, typingIndicator);
            scrollToBottom();
            
        } catch(e) {}
    }
    
    window.renameMindyConv = async function(id) {
        const title = prompt("Enter new title:");
        if (!title || !title.trim()) return;
        
        await fetch(`/mindy/conversation/${id}/title`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ title })
        });
        loadHistory();
    };
    
    window.deleteMindyConv = async function(id) {
        if (!confirm("Delete this conversation? This will permanently remove this Mindy conversation.")) return;
        
        await fetch(`/mindy/conversation/${id}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken }
        });
        loadHistory();
    };
});
