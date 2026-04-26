/**
 * Agent 推理助手 - 前端聊天逻辑
 * 支持流式输出和推理过程可视化
 */

class ChatApp {
    constructor() {
        this.messages = [];
        this.isLoading = false;
        this.currentModel = null;
        this.currentProvider = null;
        
        this.initElements();
        this.initEventListeners();
        this.loadConfig();
    }
    
    initElements() {
        this.userInput = document.getElementById('user-input');
        this.sendBtn = document.getElementById('send-btn');
        this.sendText = document.getElementById('send-text');
        this.sendIcon = document.getElementById('send-icon');
        this.loadingIcon = document.getElementById('loading-icon');
        this.messagesContainer = document.getElementById('messages');
        this.chatContainer = document.getElementById('chat-container');
        this.clearBtn = document.getElementById('clear-btn');
        this.modelInfo = document.getElementById('model-info');
        this.toast = document.getElementById('toast');
        this.toastIcon = document.getElementById('toast-icon');
        this.toastMessage = document.getElementById('toast-message');
    }
    
    initEventListeners() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.userInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
        
        this.clearBtn.addEventListener('click', () => this.clearChat());
        
        document.querySelectorAll('.quick-question').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.trim();
                this.userInput.value = text;
                this.autoResizeTextarea();
                this.userInput.focus();
            });
        });
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
    
    autoResizeTextarea() {
        this.userInput.style.height = 'auto';
        this.userInput.style.height = Math.min(this.userInput.scrollHeight, 120) + 'px';
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendBtn.disabled = loading;
        this.userInput.disabled = loading;
        
        if (loading) {
            this.sendText.textContent = '思考中...';
            this.sendIcon.classList.add('hidden');
            this.loadingIcon.classList.remove('hidden');
        } else {
            this.sendText.textContent = '发送';
            this.sendIcon.classList.remove('hidden');
            this.loadingIcon.classList.add('hidden');
        }
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
            const messagesForApi = this.messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));
            
            const messagesParam = encodeURIComponent(JSON.stringify(messagesForApi));
            const messageParam = encodeURIComponent(message);
            
            const eventSource = new EventSource(
                `/api/chat/stream?session_id=${Date.now()}&messages=${messagesParam}&message=${messageParam}`
            );
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('收到事件:', data);
                    
                    switch (data.type) {
                        case 'thinking':
                            thinkingDiv = this.addThinking(assistantMessageEl, data.content);
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
                                if (thinkingDiv) {
                                    thinkingDiv.classList.add('hidden');
                                    thinkingDiv = null;
                                }
                                fullContent += data.content;
                                this.updateMessageContent(assistantMessageEl, fullContent);
                            }
                            break;
                            
                        case 'done':
                            eventSource.close();
                            if (fullContent) {
                                this.messages.push({
                                    role: 'assistant',
                                    content: fullContent
                                });
                            }
                            this.setLoading(false);
                            
                            if (data.usage) {
                                console.log('Token使用:', data.usage);
                            }
                            break;
                            
                        case 'error':
                            eventSource.close();
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
    
    addThinking(messageEl, content) {
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
        thinkingDiv.className = 'p-2 bg-gray-50 rounded-lg border border-gray-200 mb-2';
        thinkingDiv.innerHTML = `
            <div class="flex items-center space-x-2">
                <div class="flex-shrink-0">
                    <svg class="w-4 h-4 text-gray-500 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                    </svg>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-500">
                        <span class="inline-flex items-center">
                            <span class="animate-pulse mr-1">💭</span>
                            ${this.escapeHtml(content)}
                        </span>
                    </p>
                </div>
            </div>
        `;
        
        thinkingContainer.appendChild(thinkingDiv);
        this.scrollToBottom();
        
        return thinkingDiv;
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
    
    addMessage(role, content) {
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
        
        const welcomeMsg = this.messagesContainer.querySelector('.flex.justify-center');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        if (role === 'user') {
            this.messages.push({ role: 'user', content: content });
        }
        
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
    
    clearChat() {
        if (this.messages.length === 0) {
            this.showToast('对话已经是空的了', 'info');
            return;
        }
        
        if (confirm('确定要清空所有对话吗？')) {
            this.messages = [];
            this.messagesContainer.innerHTML = `
                <div class="flex justify-center">
                    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 max-w-lg text-center">
                        <div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                            </svg>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-800 mb-2">对话已清空</h2>
                        <p class="text-gray-600 text-sm">试着问我一些新问题吧！</p>
                    </div>
                </div>
            `;
            this.showToast('对话已清空', 'success');
        }
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
