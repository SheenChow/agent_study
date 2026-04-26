/**
 * Agent 推理助手 - 前端聊天逻辑
 * 支持流式输出、推理过程可视化和会话记忆功能
 */

class ChatApp {
    constructor() {
        this.currentSessionId = null;
        this.sessions = [];
        this.isLoading = false;
        this.currentModel = null;
        this.currentProvider = null;
        this.currentEventSource = null;
        
        this.initElements();
        this.initEventListeners();
        this.loadConfig();
        this.loadSessions();
    }
    
    initElements() {
        this.userInput = document.getElementById('user-input');
        this.sendBtn = document.getElementById('send-btn');
        this.sendText = document.getElementById('send-text');
        this.sendIcon = document.getElementById('send-icon');
        this.loadingIcon = document.getElementById('loading-icon');
        this.messagesContainer = document.getElementById('messages');
        this.chatContainer = document.getElementById('chat-container');
        this.modelInfo = document.getElementById('model-info');
        this.toast = document.getElementById('toast');
        this.toastIcon = document.getElementById('toast-icon');
        this.toastMessage = document.getElementById('toast-message');
        
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.sessionList = document.getElementById('session-list');
        this.welcomeMessage = document.getElementById('welcome-message');
    }
    
    initEventListeners() {
        this.sendBtn.addEventListener('click', () => {
            if (this.isLoading) {
                this.stopGeneration();
            } else {
                this.sendMessage();
            }
        });
        
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (this.isLoading) {
                    this.stopGeneration();
                } else {
                    this.sendMessage();
                }
            }
        });
        
        this.userInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
        
        this.newChatBtn.addEventListener('click', () => this.handleNewChat());
        
        document.querySelectorAll('.quick-question').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.trim();
                this.userInput.value = text;
                this.autoResizeTextarea();
                this.userInput.focus();
            });
        });
    }
    
    async handleNewChat() {
        if (this.isLoading) {
            this.stopGeneration();
            await this.waitForLoadingToStop();
        }
        await this.createNewSession();
    }
    
    async waitForLoadingToStop() {
        let attempts = 0;
        while (this.isLoading && attempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
    }
    
    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.success) {
                this.currentModel = data.data.model;
                this.currentProvider = data.data.provider;
                this.modelInfo.textContent = `当前模型: ${data.data.model} (${data.data.provider_name})`;
            }
        } catch (error) {
            console.error('加载配置失败:', error);
            this.modelInfo.textContent = '模型加载失败';
        }
    }
    
    async loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();
            
            if (data.success) {
                this.sessions = data.data || [];
                console.log('加载会话列表:', this.sessions);
                this.renderSessionList();
                
                if (!this.currentSessionId && this.sessions.length > 0) {
                    const lastSession = this.sessions[0];
                    this.switchSession(lastSession.id);
                }
            }
        } catch (error) {
            console.error('加载会话列表失败:', error);
        }
    }
    
    renderSessionList() {
        this.sessionList.innerHTML = '';
        
        if (this.sessions.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'text-center text-gray-400 text-sm py-4';
            emptyDiv.textContent = '暂无历史对话';
            this.sessionList.appendChild(emptyDiv);
            return;
        }
        
        this.sessions.forEach(session => {
            const sessionItem = this.createSessionItem(session);
            this.sessionList.appendChild(sessionItem);
        });
    }
    
    createSessionItem(session) {
        const div = document.createElement('div');
        div.className = `session-item p-2 rounded-lg cursor-pointer border border-transparent hover:bg-gray-50 transition-colors group ${
            this.currentSessionId === session.id ? 'active bg-blue-50 border-blue-200' : ''
        }`;
        div.dataset.sessionId = session.id;
        
        const title = session.title || '新对话';
        const displayTitle = title.length > 20 ? title.substring(0, 20) + '...' : title;
        
        const updatedAt = new Date(session.updated_at);
        const timeStr = this.formatTime(updatedAt);
        
        const messageCount = session.message_count !== undefined && session.message_count !== null 
            ? session.message_count 
            : 0;
        
        div.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1 min-w-0 session-content">
                    <div class="flex items-center space-x-2">
                        <svg class="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                        </svg>
                        <span class="text-sm text-gray-700 truncate">${this.escapeHtml(displayTitle)}</span>
                    </div>
                    <div class="text-xs text-gray-400 mt-1 ml-6">${timeStr} · ${messageCount} 条消息</div>
                </div>
                <button class="session-delete-btn p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors opacity-0 group-hover:opacity-100" title="删除会话">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                </button>
            </div>
        `;
        
        const deleteBtn = div.querySelector('.session-delete-btn');
        const contentDiv = div.querySelector('.session-content');
        
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.confirmAndDeleteSession(session.id, session.title);
        });
        
        contentDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            this.handleSessionClick(session.id);
        });
        
        div.addEventListener('click', (e) => {
            if (e.target === div || e.target.closest('.session-content')) {
                this.handleSessionClick(session.id);
            }
        });
        
        return div;
    }
    
    async handleSessionClick(sessionId) {
        if (this.currentSessionId === sessionId) {
            return;
        }
        
        if (this.isLoading) {
            this.stopGeneration();
            await this.waitForLoadingToStop();
        }
        
        await this.switchSession(sessionId);
    }
    
    confirmAndDeleteSession(sessionId, sessionTitle) {
        const title = sessionTitle || '此对话';
        if (confirm(`确定要删除对话"${title}"吗？此操作不可撤销。`)) {
            this.deleteSession(sessionId);
        }
    }
    
    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        const oneDay = 24 * 60 * 60 * 1000;
        
        if (diff < 60 * 1000) {
            return '刚刚';
        } else if (diff < 60 * 60 * 1000) {
            return `${Math.floor(diff / (60 * 1000))}分钟前`;
        } else if (diff < oneDay) {
            return `${Math.floor(diff / (60 * 60 * 1000))}小时前`;
        } else if (diff < 7 * oneDay) {
            return `${Math.floor(diff / oneDay)}天前`;
        } else {
            return date.toLocaleDateString('zh-CN');
        }
    }
    
    async createNewSession() {
        try {
            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: '新对话' })
            });
            
            const data = await response.json();
            
            if (data.success) {
                const newSession = data.data;
                this.sessions.unshift(newSession);
                this.renderSessionList();
                this.currentSessionId = newSession.id;
                this.clearMessages();
                this.showWelcomeMessage();
                this.renderSessionList();
                this.showToast('新对话已创建', 'success');
            }
        } catch (error) {
            console.error('创建会话失败:', error);
            this.showToast('创建会话失败', 'error');
        }
    }
    
    async switchSession(sessionId) {
        if (this.currentSessionId === sessionId) {
            return;
        }
        
        this.currentSessionId = sessionId;
        this.renderSessionList();
        
        try {
            const response = await fetch(`/api/sessions/${sessionId}`);
            const data = await response.json();
            
            if (data.success) {
                this.clearMessages();
                
                const messages = data.data.messages || [];
                console.log('切换会话，加载消息数:', messages.length);
                
                if (messages.length === 0) {
                    this.showWelcomeMessage();
                } else {
                    this.hideWelcomeMessage();
                    messages.forEach(msg => {
                        if (msg.role === 'user' || msg.role === 'assistant') {
                            this.addMessage(msg.role, msg.content, false);
                        }
                    });
                }
                
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('加载会话失败:', error);
            this.showToast('加载会话失败', 'error');
        }
    }
    
    async deleteSession(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.sessions = this.sessions.filter(s => s.id !== sessionId);
                
                if (this.currentSessionId === sessionId) {
                    if (this.sessions.length > 0) {
                        this.currentSessionId = this.sessions[0].id;
                        this.clearMessages();
                        this.switchSession(this.currentSessionId);
                    } else {
                        this.currentSessionId = null;
                        this.clearMessages();
                        this.showWelcomeMessage();
                    }
                }
                
                this.renderSessionList();
                this.showToast('会话已删除', 'success');
            }
        } catch (error) {
            console.error('删除会话失败:', error);
            this.showToast('删除会话失败', 'error');
        }
    }
    
    showWelcomeMessage() {
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'flex';
        }
    }
    
    hideWelcomeMessage() {
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }
    }
    
    clearMessages() {
        const welcomeMsg = this.messagesContainer.querySelector('#welcome-message');
        this.messagesContainer.innerHTML = '';
        if (welcomeMsg) {
            this.messagesContainer.appendChild(welcomeMsg);
        }
    }
    
    autoResizeTextarea() {
        this.userInput.style.height = 'auto';
        this.userInput.style.height = Math.min(this.userInput.scrollHeight, 120) + 'px';
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendBtn.disabled = false;
        this.userInput.disabled = loading;
        
        if (loading) {
            this.sendText.textContent = '停止';
            this.sendIcon.classList.add('hidden');
            this.loadingIcon.classList.remove('hidden');
        } else {
            this.sendText.textContent = '发送';
            this.sendIcon.classList.remove('hidden');
            this.loadingIcon.classList.add('hidden');
        }
    }
    
    stopGeneration() {
        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }
        this.setLoading(false);
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        
        if (!message) {
            this.showToast('请输入问题', 'error');
            return;
        }
        
        if (this.isLoading) {
            return;
        }
        
        if (!this.currentSessionId) {
            await this.createNewSession();
        }
        
        this.hideWelcomeMessage();
        
        this.addMessage('user', message);
        this.userInput.value = '';
        this.autoResizeTextarea();
        
        const assistantMessageEl = this.addMessage('assistant', '');
        this.setLoading(true);
        
        let thinkingDiv = null;
        let planningDiv = null;
        let toolCallDiv = null;
        let fullContent = '';
        let hasToolCall = false;
        
        try {
            const messageParam = encodeURIComponent(message);
            const sessionParam = this.currentSessionId ? `&memory_session_id=${encodeURIComponent(this.currentSessionId)}` : '';
            
            const eventSource = new EventSource(
                `/api/chat/stream?message=${messageParam}${sessionParam}`
            );
            this.currentEventSource = eventSource;
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('收到事件:', data);
                    
                    if (data.memory_session_id) {
                        this.currentSessionId = data.memory_session_id;