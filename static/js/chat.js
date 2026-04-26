/**
 * Agent 推理助手 - 前端聊天逻辑
 * 支持流式输出、推理过程可视化和会话记忆功能
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
        this.stopBtn = document.getElementById('stop-btn');
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
        
        this.newChatBtn.addEventListener('click', () => this.createNewSession());
        
        this.stopBtn.addEventListener('click', () => this.stopGeneration());
        
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
        console.log('[DEBUG] === loadSessions() 开始 ===');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.error('[ERROR] loadSessions() 请求超时 (10秒)');
            controller.abort();
        }, 10000);
        
        try {
            console.log('[DEBUG] 准备发送 fetch 请求...');
            
            const response = await fetch('/api/sessions', {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                },
                signal: controller.signal
            });
            
            console.log('[DEBUG] fetch 响应收到, status:', response.status);
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            console.log('[DEBUG] 准备解析 JSON...');
            const text = await response.text();
            console.log('[DEBUG] 原始响应文本:', text.substring(0, 200) + (text.length > 200 ? '...' : ''));
            
            let data;
            try {
                data = JSON.parse(text);
            } catch (jsonError) {
                console.error('[ERROR] JSON 解析失败:', jsonError);
                throw jsonError;
            }
            
            console.log('[DEBUG] 会话列表 API 返回:', data);
            console.log('[DEBUG] API 返回的每个会话详情:');
            if (data.data && data.data.length > 0) {
                data.data.forEach((s, i) => {
                    console.log(`  [${i}] id=${s.id}, title=${s.title}, message_count=${s.message_count}`);
                });
            }
            
            if (data.success) {
                console.log('[DEBUG] 更新 this.sessions 之前:', this.sessions.map(s => ({id: s.id, message_count: s.message_count})));
                this.sessions = data.data || [];
                console.log('[DEBUG] 更新 this.sessions 之后:', this.sessions.map(s => ({id: s.id, message_count: s.message_count})));
                
                console.log('[DEBUG] 准备调用 renderSessionList()...');
                this.renderSessionList();
                console.log('[DEBUG] renderSessionList() 完成');
                
                if (this.sessions.length > 0 && !this.currentSessionId) {
                    const lastSession = this.sessions[0];
                    this.switchSession(lastSession.id);
                }
            }
            
            console.log('[DEBUG] === loadSessions() 成功完成 ===');
            
        } catch (error) {
            clearTimeout(timeoutId);
            console.error('[ERROR] loadSessions() 失败:', error);
            console.error('[ERROR] 错误类型:', error.name);
            console.error('[ERROR] 错误消息:', error.message);
            if (error.stack) {
                console.error('[ERROR] 堆栈:', error.stack);
            }
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
        console.log('[DEBUG] 创建会话项:', session);
        console.log('[DEBUG] message_count 类型:', typeof session.message_count, '值:', session.message_count);
        
        const div = document.createElement('div');
        div.className = `session-item p-2 rounded-lg cursor-pointer border border-transparent hover:bg-gray-50 transition-colors group ${
            this.currentSessionId === session.id ? 'active bg-blue-50 border-blue-200' : ''
        }`;
        div.dataset.sessionId = session.id;
        
        const title = session.title || '新对话';
        const displayTitle = title.length > 20 ? title.substring(0, 20) + '...' : title;
        
        const updatedAt = new Date(session.updated_at);
        const timeStr = this.formatTime(updatedAt);
        
        const messageCount = typeof session.message_count === 'number' ? session.message_count : 0;
        console.log('[DEBUG] 最终显示的消息数量:', messageCount);
        
        div.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2">
                        <svg class="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                        </svg>
                        <span class="text-sm text-gray-700 truncate">${this.escapeHtml(displayTitle)}</span>
                    </div>
                    <div class="text-xs text-gray-400 mt-1 ml-6">${timeStr} · ${messageCount} 条消息</div>
                </div>
                <button class="session-delete-btn p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors opacity-0 group-hover:opacity-100" title="删除会话" data-session-id="${session.id}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                </button>
            </div>
        `;
        
        div.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.session-delete-btn');
            if (deleteBtn) {
                return;
            }
            this.switchSession(session.id);
        });

        const deleteBtn = div.querySelector('.session-delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const sessionIdToDelete = session.id;
                console.log('准备删除会话:', sessionIdToDelete);
                if (confirm('确定要删除这个对话吗？')) {
                    console.log('用户确认删除:', sessionIdToDelete);
                    this.deleteSession(sessionIdToDelete);
                } else {
                    console.log('用户取消删除');
                }
            });
        }
        
        return div;
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
        if (this.isLoading) {
            if (confirm('当前有正在进行的对话，确定要新建对话吗？这将停止当前的生成。')) {
                this.stopGeneration();
            } else {
                return;
            }
        }
        
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
                this.switchSession(newSession.id);
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
        
        if (this.isLoading) {
            if (confirm('当前有正在进行的对话，确定要切换吗？这将停止当前的生成。')) {
                this.stopGeneration();
            } else {
                return;
            }
        }
        
        this.currentSessionId = sessionId;
        this.renderSessionList();
        
        try {
            const response = await fetch(`/api/sessions/${sessionId}`);
            const data = await response.json();
            
            if (data.success) {
                this.clearMessages();
                
                const messages = data.data.messages || [];
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
                        this.switchSession(this.sessions[0].id);
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
    
    stopGeneration() {
        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }
        this.setLoading(false);
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
            this.sendBtn.classList.add('hidden');
            this.stopBtn.classList.remove('hidden');
        } else {
            this.sendText.textContent = '发送';
            this.sendIcon.classList.remove('hidden');
            this.loadingIcon.classList.add('hidden');
            this.sendBtn.classList.remove('hidden');
            this.stopBtn.classList.add('hidden');
        }
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        
        console.log('[DEBUG] === 开始发送消息 ===');
        console.log('[DEBUG] 当前会话ID:', this.currentSessionId);
        console.log('[DEBUG] 当前会话列表:', this.sessions);
        
        // 找到当前会话
        if (this.currentSessionId) {
            const currentSession = this.sessions.find(s => s.id === this.currentSessionId);
            console.log('[DEBUG] 当前会话详情:', currentSession);
            if (currentSession) {
                console.log('[DEBUG] 发送前消息数量:', currentSession.message_count);
            }
        }
        
        if (!message) {
            this.showToast('请输入问题', 'error');
            return;
        }
        
        if (this.isLoading) {
            this.stopGeneration();
            return;
        }
        
        if (!this.currentSessionId) {
            try {
                const response = await fetch('/api/sessions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ title: message.length > 30 ? message.substring(0, 30) : message })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const newSession = data.data;
                    this.currentSessionId = newSession.id;
                    this.sessions.unshift(newSession);
                    this.renderSessionList();
                }
            } catch (error) {
                console.error('创建会话失败:', error);
                this.showToast('创建会话失败', 'error');
                return;
            }
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
                    }
                    
                    switch (data.type) {
                        case 'thinking':
                            const status = data.status || (data.metadata ? data.metadata.status : null);
                            const content = data.content;
                            
                            if (content === '正在分析问题...' || content === '正在根据信息生成回答...') {
                                if (!thinkingDiv) {
                                    thinkingDiv = this.addThinking(assistantMessageEl, content, 'processing');
                                }
                            } else {
                                if (thinkingDiv && status === 'complete') {
                                    this.updateThinking(thinkingDiv, content, 'complete');
                                } else {
                                    thinkingDiv = this.addThinking(assistantMessageEl, content, status || 'complete');
                                }
                            }
                            break;
                            
                        case 'planning':
                            planningDiv = this.addPlanning(assistantMessageEl, data.content, data.tool);
                            break;
                            
                        case 'tool_call':
                            hasToolCall = true;
                            toolCallDiv = this.addToolCall(assistantMessageEl, data.tool, data.query);
                            break;
                            
                        case 'tool_result':
                            if (toolCallDiv) {
                                this.updateToolResult(toolCallDiv, data.tool, data.success, data.result_count);
                            }
                            break;
                            
                        case 'text':
                            if (data.content) {
                                if (hasToolCall && !fullContent) {
                                    this.addSeparator(assistantMessageEl);
                                }
                                fullContent += data.content;
                                this.updateMessageContent(assistantMessageEl, fullContent);
                            }
                            break;
                            
                        case 'done':
                            console.log('[DEBUG] 收到 done 事件，准备关闭连接并刷新会话列表');
                            eventSource.close();
                            this.currentEventSource = null;
                            this.setLoading(false);
                            
                            if (data.usage) {
                                console.log('Token使用:', data.usage);
                            }
                            
                            console.log('[DEBUG] 延迟 100ms 后调用 loadSessions()...');
                            setTimeout(() => {
                                console.log('[DEBUG] 现在调用 loadSessions() 刷新会话列表');
                                this.loadSessions().then(() => {
                                    console.log('[DEBUG] loadSessions() Promise 完成');
                                }).catch((err) => {
                                    console.error('[ERROR] loadSessions() Promise 失败:', err);
                                });
                            }, 100);
                            break;
                            
                        case 'error':
                            eventSource.close();
                            this.currentEventSource = null;
                            this.updateMessageContent(assistantMessageEl, `❌ 错误: ${data.content}`);
                            this.setLoading(false);
                            this.showToast(data.content, 'error');
                            break;
                    }
                } catch (e) {
                    console.error('解析消息失败:', e);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('SSE连接错误:', error);
                eventSource.close();
                this.currentEventSource = null;
                
                if (!fullContent) {
                    this.updateMessageContent(assistantMessageEl, '❌ 连接失败，请检查网络或API配置');
                }
                
                this.setLoading(false);
                this.showToast('连接出错', 'error');
            };
            
        } catch (error) {
            console.error('发送消息失败:', error);
            this.updateMessageContent(assistantMessageEl, `❌ 发送失败: ${error.message}`);
            this.setLoading(false);
            this.showToast('发送失败', 'error');
        }
    }
    
    addThinking(messageEl, content, status = 'processing') {
        const bubbleDiv = messageEl.querySelector('.message-bubble');
        if (!bubbleDiv) return null;
        
        let thinkingContainer = bubbleDiv.querySelector('.thinking-container');
        if (!thinkingContainer) {
            thinkingContainer = document.createElement('div');
            thinkingContainer.className = 'thinking-container mb-2';
            const contentDiv = bubbleDiv.querySelector('.message-content');
            if (contentDiv) {
                bubbleDiv.insertBefore(thinkingContainer, contentDiv);
            } else {
                bubbleDiv.appendChild(thinkingContainer);
            }
        }
        
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = `p-2 rounded-lg border mb-2 ${status === 'processing' ? 'bg-gray-50 border-gray-200' : 'bg-green-50 border-green-200'}`;
        
        const pulseClass = status === 'processing' ? 'animate-pulse' : '';
        const iconColor = status === 'processing' ? 'text-gray-500' : 'text-green-600';
        const textColor = status === 'processing' ? 'text-gray-500' : 'text-green-700';
        const iconSvg = status === 'processing' 
            ? `<svg class="w-4 h-4 ${iconColor} animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
               </svg>`
            : `<svg class="w-4 h-4 ${iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
               </svg>`;
        
        thinkingDiv.innerHTML = `
            <div class="flex items-start space-x-2">
                <div class="flex-shrink-0 mt-0.5">
                    ${iconSvg}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm ${textColor}">
                        <span class="inline-flex items-start">
                            <span class="${pulseClass} mr-1">💭</span>
                            <span class="whitespace-pre-wrap">${this.escapeHtml(content)}</span>
                        </span>
                    </p>
                </div>
            </div>
        `;
        
        thinkingContainer.appendChild(thinkingDiv);
        this.scrollToBottom();
        
        return thinkingDiv;
    }
    
    updateThinking(thinkingDiv, content, status = 'complete') {
        if (!thinkingDiv) return;
        
        const bubbleClass = status === 'processing' ? 'bg-gray-50 border-gray-200' : 'bg-green-50 border-green-200';
        const iconColor = status === 'processing' ? 'text-gray-500' : 'text-green-600';
        const textColor = status === 'processing' ? 'text-gray-500' : 'text-green-700';
        const iconSvg = status === 'processing' 
            ? `<svg class="w-4 h-4 ${iconColor} animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
               </svg>`
            : `<svg class="w-4 h-4 ${iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
               </svg>`;
        
        thinkingDiv.className = `p-2 rounded-lg border mb-2 ${bubbleClass}`;
        thinkingDiv.innerHTML = `
            <div class="flex items-start space-x-2">
                <div class="flex-shrink-0 mt-0.5">
                    ${iconSvg}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm ${textColor}">
                        <span class="inline-flex items-start">
                            <span class="mr-1">💭</span>
                            <span class="whitespace-pre-wrap">${this.escapeHtml(content)}</span>
                        </span>
                    </p>
                </div>
            </div>
        `;
        
        this.scrollToBottom();
    }
    
    addPlanning(messageEl, content, tool) {
        const bubbleDiv = messageEl.querySelector('.message-bubble');
        if (!bubbleDiv) return null;
        
        let thinkingContainer = bubbleDiv.querySelector('.thinking-container');
        if (!thinkingContainer) {
            thinkingContainer = document.createElement('div');
            thinkingContainer.className = 'thinking-container mb-2';
            const contentDiv = bubbleDiv.querySelector('.message-content');
            if (contentDiv) {
                bubbleDiv.insertBefore(thinkingContainer, contentDiv);
            } else {
                bubbleDiv.appendChild(thinkingContainer);
            }
        }
        
        const planningDiv = document.createElement('div');
        planningDiv.className = 'p-2 bg-blue-50 rounded-lg border border-blue-200 mb-2';
        
        let iconHtml = '';
        if (tool === 'web_search') {
            iconHtml = `<svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>`;
        } else {
            iconHtml = `<svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>`;
        }
        
        planningDiv.innerHTML = `
            <div class="flex items-center space-x-2">
                <div class="flex-shrink-0">
                    ${iconHtml}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-blue-700">
                        <span class="font-medium">📋 规划：</span>
                        ${this.escapeHtml(content)}
                    </p>
                </div>
            </div>
        `;
        
        thinkingContainer.appendChild(planningDiv);
        this.scrollToBottom();
        
        return planningDiv;
    }
    
    addToolCall(messageEl, toolName, query) {
        const bubbleDiv = messageEl.querySelector('.message-bubble');
        if (!bubbleDiv) return null;
        
        let thinkingContainer = bubbleDiv.querySelector('.thinking-container');
        if (!thinkingContainer) {
            thinkingContainer = document.createElement('div');
            thinkingContainer.className = 'thinking-container mb-2';
            const contentDiv = bubbleDiv.querySelector('.message-content');
            if (contentDiv) {
                bubbleDiv.insertBefore(thinkingContainer, contentDiv);
            } else {
                bubbleDiv.appendChild(thinkingContainer);
            }
        }
        
        const toolCallDiv = document.createElement('div');
        toolCallDiv.className = 'p-2 bg-amber-50 rounded-lg border border-amber-200 mb-2';
        toolCallDiv.dataset.tool = toolName;
        
        let iconHtml = '';
        let displayName = '';
        
        if (toolName === 'web_search') {
            iconHtml = `<svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>`;
            displayName = '搜索';
        } else {
            iconHtml = `<svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>`;
            displayName = toolName;
        }
        
        toolCallDiv.innerHTML = `
            <div class="flex items-center space-x-2">
                <div class="flex-shrink-0">
                    <span class="inline-block w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-amber-700">
                        <span class="font-medium">🔍 ${displayName}中：</span>
                        "${this.escapeHtml(query || '')}"
                    </p>
                </div>
            </div>
        `;
        
        thinkingContainer.appendChild(toolCallDiv);
        this.scrollToBottom();
        
        return toolCallDiv;
    }
    
    updateToolResult(toolCallDiv, toolName, success, resultCount) {
        if (!toolCallDiv) return;
        
        let iconHtml = '';
        let statusText = '';
        let statusClass = '';
        
        if (success) {
            iconHtml = `<svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>`;
            statusText = `完成，找到 ${resultCount || 0} 条结果`;
            statusClass = 'text-green-700';
            toolCallDiv.className = 'p-2 bg-green-50 rounded-lg border border-green-200 mb-2';
        } else {
            iconHtml = `<svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>`;
            statusText = '执行失败';
            statusClass = 'text-red-700';
            toolCallDiv.className = 'p-2 bg-red-50 rounded-lg border border-red-200 mb-2';
        }
        
        const pElement = toolCallDiv.querySelector('p');
        if (pElement) {
            pElement.innerHTML = `<span class="font-medium">✅ 搜索${statusText}</span>`;
            pElement.className = `text-sm ${statusClass}`;
        }
        
        const spinner = toolCallDiv.querySelector('.animate-spin');
        if (spinner) {
            spinner.outerHTML = iconHtml;
        }
        
        this.scrollToBottom();
    }
    
    addSeparator(messageEl) {
        const bubbleDiv = messageEl.querySelector('.message-bubble');
        if (!bubbleDiv) return;
        
        const separator = document.createElement('div');
        separator.className = 'my-2 border-t border-gray-200';
        separator.innerHTML = '<div class="text-center text-xs text-gray-400 my-1">— 以上是搜索过程 —</div>';
        
        const contentDiv = bubbleDiv.querySelector('.message-content');
        if (contentDiv) {
            const thinkingContainer = bubbleDiv.querySelector('.thinking-container');
            if (thinkingContainer) {
                bubbleDiv.insertBefore(separator, contentDiv);
            }
        }
    }
    
    addMessage(role, content, addToHistory = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-appear ${role === 'user' ? 'flex justify-end' : 'flex justify-start'}`;
        
        const bubbleDiv = document.createElement('div');
        
        if (role === 'user') {
            bubbleDiv.className = 'message-bubble max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm';
            bubbleDiv.innerHTML = this.escapeHtml(content);
        } else {
            bubbleDiv.className = 'message-bubble max-w-[80%] bg-white text-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-200';
            
            const headerDiv = document.createElement('div');
            headerDiv.className = 'flex items-center space-x-2 mb-1';
            headerDiv.innerHTML = `
                <div class="w-6 h-6 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                    </svg>
                </div>
                <span class="text-xs text-gray-500">Agent</span>
            `;
            bubbleDiv.appendChild(headerDiv);
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content whitespace-pre-wrap break-words';
            contentDiv.innerHTML = this.escapeHtml(content) || '<span class="typing-cursor text-blue-500">▌</span>';
            bubbleDiv.appendChild(contentDiv);
        }
        
        messageDiv.appendChild(bubbleDiv);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    updateMessageContent(messageEl, content) {
        const contentDiv = messageEl.querySelector('.message-content');
        if (contentDiv) {
            const displayContent = content || '<span class="typing-cursor text-blue-500">▌</span>';
            contentDiv.innerHTML = this.escapeHtml(displayContent).replace(/\n/g, '<br>');
        }
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        requestAnimationFrame(() => {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showToast(message, type = 'info') {
        const icons = {
            success: '<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
            error: '<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
            info: '<svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
        };
        
        this.toastIcon.innerHTML = icons[type] || icons.info;
        this.toastMessage.textContent = message;
        
        this.toast.classList.remove('translate-x-full');
        
        setTimeout(() => {
            this.toast.classList.add('translate-x-full');
        }, 3000);
    }
}


document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
