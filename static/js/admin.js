/**
 * 后台管理 - 前端逻辑
 */

class AdminApp {
    constructor() {
        this.currentProvider = 'qwen';
        this.currentConfig = null;
        this.defaultSystemPrompt = '你是一个智能推理助手。当用户提出问题时，你需要：\n1. 仔细分析问题\n2. 逐步思考解决方法\n3. 给出最终答案';
        
        this.providerHints = {
            qwen: '获取方式: <a href="https://dashscope.console.aliyun.com/" target="_blank" class="text-blue-500 hover:underline">阿里云DashScope控制台</a>',
            openai: '获取方式: <a href="https://platform.openai.com/api-keys" target="_blank" class="text-blue-500 hover:underline">OpenAI平台</a>'
        };
        
        this.modelDescriptions = {};
        
        this.initElements();
        this.initEventListeners();
        this.loadConfig();
    }
    
    initElements() {
        this.providerSelect = document.getElementById('provider-select');
        this.apiKeyInput = document.getElementById('api-key-input');
        this.toggleApiKeyBtn = document.getElementById('toggle-api-key');
        this.providerHint = document.getElementById('provider-hint');
        this.modelSelect = document.getElementById('model-select');
        this.modelDescription = document.getElementById('model-description');
        this.systemPromptInput = document.getElementById('system-prompt-input');
        this.resetPromptBtn = document.getElementById('reset-prompt-btn');
        this.testConnectionBtn = document.getElementById('test-connection-btn');
        this.testIcon = document.getElementById('test-icon');
        this.testLoading = document.getElementById('test-loading');
        this.testText = document.getElementById('test-text');
        this.saveConfigBtn = document.getElementById('save-config-btn');
        this.saveIcon = document.getElementById('save-icon');
        this.saveLoading = document.getElementById('save-loading');
        this.saveText = document.getElementById('save-text');
        this.toast = document.getElementById('toast');
        this.toastIcon = document.getElementById('toast-icon');
        this.toastMessage = document.getElementById('toast-message');
    }
    
    initEventListeners() {
        this.providerSelect.addEventListener('change', () => {
            this.currentProvider = this.providerSelect.value;
            this.updateProviderHint();
            this.loadModels();
        });
        
        this.toggleApiKeyBtn.addEventListener('click', () => {
            this.toggleApiKeyVisibility();
        });
        
        this.modelSelect.addEventListener('change', () => {
            this.updateModelDescription();
        });
        
        this.resetPromptBtn.addEventListener('click', () => {
            this.systemPromptInput.value = this.defaultSystemPrompt;
            this.showToast('已恢复默认提示词', 'success');
        });
        
        this.testConnectionBtn.addEventListener('click', () => {
            this.testConnection();
        });
        
        this.saveConfigBtn.addEventListener('click', () => {
            this.saveConfig();
        });
    }
    
    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.success) {
                this.currentConfig = data.data;
                this.currentProvider = data.data.provider;
                
                this.providerSelect.value = data.data.provider;
                this.updateProviderHint();
                
                if (data.data.api_key && data.data.api_key.length > 0) {
                    this.apiKeyInput.placeholder = '已配置（点击显示/隐藏）';
                }
                
                if (data.data.system_prompt) {
                    this.systemPromptInput.value = data.data.system_prompt;
                }
                
                await this.loadModels();
                
                if (data.data.model) {
                    this.modelSelect.value = data.data.model;
                    this.updateModelDescription();
                }
            }
        } catch (error) {
            console.error('加载配置失败:', error);
            this.showToast('加载配置失败', 'error');
        }
    }
    
    updateProviderHint() {
        this.providerHint.innerHTML = this.providerHints[this.currentProvider] || '';
    }
    
    toggleApiKeyVisibility() {
        if (this.apiKeyInput.type === 'password') {
            this.apiKeyInput.type = 'text';
            this.toggleApiKeyBtn.textContent = '隐藏';
        } else {
            this.apiKeyInput.type = 'password';
            this.toggleApiKeyBtn.textContent = '显示';
        }
    }
    
    async loadModels() {
        try {
            const response = await fetch(`/api/models?provider=${this.currentProvider}`);
            const data = await response.json();
            
            if (data.success) {
                this.modelSelect.innerHTML = '';
                this.modelDescriptions = {};
                
                data.data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.id;
                    option.textContent = model.name;
                    this.modelSelect.appendChild(option);
                    
                    this.modelDescriptions[model.id] = model.description;
                });
                
                this.updateModelDescription();
            }
        } catch (error) {
            console.error('加载模型列表失败:', error);
        }
    }
    
    updateModelDescription() {
        const selectedModel = this.modelSelect.value;
        const description = this.modelDescriptions[selectedModel] || '';
        this.modelDescription.textContent = description;
    }
    
    async testConnection() {
        const apiKey = this.apiKeyInput.value.trim();
        
        this.setTestLoading(true);
        
        try {
            const response = await fetch('/api/test-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: this.currentProvider,
                    api_key: apiKey || undefined
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('连接测试成功！API Key有效', 'success');
            } else {
                this.showToast(data.error || '连接测试失败', 'error');
            }
        } catch (error) {
            console.error('测试连接失败:', error);
            this.showToast('网络错误', 'error');
        } finally {
            this.setTestLoading(false);
        }
    }
    
    async saveConfig() {
        const apiKey = this.apiKeyInput.value.trim();
        const model = this.modelSelect.value;
        const systemPrompt = this.systemPromptInput.value;
        
        this.setSaveLoading(true);
        
        try {
            const updateData = {
                provider: this.currentProvider,
                model: model,
                system_prompt: systemPrompt
            };
            
            if (apiKey) {
                updateData.api_key = apiKey;
            }
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('配置保存成功！', 'success');
            } else {
                this.showToast(data.error || '保存失败', 'error');
            }
        } catch (error) {
            console.error('保存配置失败:', error);
            this.showToast('网络错误', 'error');
        } finally {
            this.setSaveLoading(false);
        }
    }
    
    setTestLoading(loading) {
        this.testConnectionBtn.disabled = loading;
        
        if (loading) {
            this.testIcon.classList.add('hidden');
            this.testLoading.classList.remove('hidden');
            this.testText.textContent = '测试中...';
        } else {
            this.testIcon.classList.remove('hidden');
            this.testLoading.classList.add('hidden');
            this.testText.textContent = '测试连接';
        }
    }
    
    setSaveLoading(loading) {
        this.saveConfigBtn.disabled = loading;
        
        if (loading) {
            this.saveIcon.classList.add('hidden');
            this.saveLoading.classList.remove('hidden');
            this.saveText.textContent = '保存中...';
        } else {
            this.saveIcon.classList.remove('hidden');
            this.saveLoading.classList.add('hidden');
            this.saveText.textContent = '保存配置';
        }
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
    new AdminApp();
});
