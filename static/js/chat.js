/**
 * Agent 推理助手 - 前端聊天逻辑
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
            
            let fullContent = '';
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'text' && data.content) {
                        fullContent += data.content;
                        this.updateMessageContent(assistantMessageEl, fullContent);
                    } else if (data.type === 'done') {
                        eventSource.close();
                        this.messages.push({
                            role: 'assistant',
                            content: fullContent
                        });
                        this.setLoading(false);
                        
                        if (data.usage) {
                            console.log('Token使用:', data.usage);
                        }
                    } else if (data.type === 'error') {
                        eventSource.close();
                        this.updateMessageContent(assistantMessageEl, `❌ 错误: ${data.content}`);
                        this.setLoading(false);
                        this.showToast(data.content, 'error');
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
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-appear ${role === 'user' ? 'flex justify-end' : 'flex justify-start'}`;
        
        const bubbleDiv = document.createElement('div');
        
        if (role === 'user') {
            bubbleDiv.className = 'max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm';
            bubbleDiv.innerHTML = this.escapeHtml(content);
        } else {
            bubbleDiv.className = 'max-w-[80%] bg-white text-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-200';
            
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
