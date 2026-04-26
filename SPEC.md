# Agent Web 应用规格说明书 (Spec)

## 版本信息
- **版本**: v1.0.0
- **日期**: 2026-04-25
- **状态**: 开发中
- **作者**: AI Assistant

---

## 一、项目概述

### 1.1 项目背景
从命令行Demo升级为Web应用，支持用户交互、流式输出和配置管理。

### 1.2 项目目标
- ✅ 提供友好的Web界面，让用户可以输入问题
- ✅ 实现大模型输出的流式展示（打字机效果）
- ✅ 提供后台管理页面，支持模型和服务商配置切换
- ✅ 保持代码轻量、易维护、易扩展

### 1.3 目标用户
- 学习Agent知识的开发者
- 需要快速测试大模型能力的用户
- 需要管理多模型配置的用户

---

## 二、技术架构

### 2.1 技术栈选型

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **后端框架** | Flask | 3.0+ | 轻量级Python Web框架 |
| **流式传输** | SSE (Server-Sent Events) | - | 服务器向客户端推送实时数据 |
| **前端** | HTML + CSS + JavaScript | ES6+ | 原生开发，无构建依赖 |
| **样式框架** | Tailwind CSS | 3.x | CDN引入，快速构建UI |
| **配置存储** | JSON文件 + .env | - | 简单灵活，便于版本控制 |
| **LLM SDK** | dashscope | 1.x | 阿里云千问模型SDK |

### 2.2 项目结构

```
agent_study/
├── app.py                    # Flask主应用入口
├── config.py                 # 配置管理模块
├── agents/
│   ├── __init__.py
│   └── llm_agent.py          # 统一LLM调用接口（支持多服务商）
├── static/
│   ├── css/
│   │   └── style.css         # 自定义样式（可选）
│   └── js/
│       ├── chat.js           # 前端聊天逻辑
│       └── admin.js          # 后台管理逻辑
├── templates/
│   ├── index.html            # 前端用户页面
│   └── admin.html            # 后台管理页面
├── data/
│   └── config.json           # 运行时配置存储
├── .env                      # 环境变量（API Key等，git忽略）
├── .env.example              # 环境变量模板
├── requirements.txt          # Python依赖文件
├── SPEC.md                   # 本文档，规格说明书
└── qwen_demo.py              # 原命令行Demo（保留参考）
```

### 2.3 数据流架构

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   前端页面   │◄──────►│  Flask后端   │◄──────►│  LLM服务    │
│  (浏览器)    │  HTTP   │  (Python)   │  API   │ (千问/OpenAI)│
└─────────────┘         └─────────────┘         └─────────────┘
       │                       │                       │
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  用户输入    │         │  配置管理    │         │  模型调用    │
│  问题输入框  │         │  JSON存储   │         │  流式输出    │
│  对话历史    │         │  API Key管理│         │  SSE推送    │
└─────────────┘         └─────────────┘         └─────────────┘
```

---

## 三、功能规格

### 3.1 功能模块清单

| 模块 | 功能点 | 优先级 | 状态 |
|------|--------|--------|------|
| **用户聊天** | 输入问题 | P0 | 待开发 |
| **用户聊天** | 流式输出响应 | P0 | 待开发 |
| **用户聊天** | 对话历史展示 | P1 | 待开发 |
| **用户聊天** | 清空对话 | P1 | 待开发 |
| **后台管理** | 查看当前配置 | P0 | 待开发 |
| **后台管理** | 切换服务商 | P0 | 待开发 |
| **后台管理** | 配置API Key | P0 | 待开发 |
| **后台管理** | 选择模型 | P0 | 待开发 |
| **后台管理** | 保存配置 | P0 | 待开发 |
| **配置管理** | 配置加载 | P0 | 待开发 |
| **配置管理** | 配置保存 | P0 | 待开发 |
| **配置管理** | 配置验证 | P1 | 待开发 |

### 3.2 详细功能规格

#### 3.2.1 用户聊天页面 (`/`)

**页面布局**：
- 顶部：标题栏（"Agent 推理助手"）
- 中部：对话区域（滚动显示历史消息）
- 底部：输入区域（输入框 + 发送按钮）

**消息气泡样式**：
- 用户消息：右侧，蓝色背景
- 模型消息：左侧，白色背景
- 流式输出时：模型消息逐字显示（打字机效果）

**功能点**：

| 功能 | 描述 | 输入 | 输出 | 异常处理 |
|------|------|------|------|----------|
| 发送消息 | 用户输入问题并发送 | 文本内容 | 发送成功，开始接收响应 | 空输入提示、网络错误提示 |
| 流式接收 | 逐字显示模型响应 | SSE事件流 | 打字机效果显示 | 连接断开提示、重新连接 |
| 清空对话 | 清空所有历史消息 | 按钮点击 | 对话区域清空 | 确认弹窗（可选） |

#### 3.2.2 后台管理页面 (`/admin`)

**页面布局**：
- 顶部：标题栏（"后台管理" + 返回首页链接）
- 中部：配置表单区域
- 底部：保存按钮 + 状态提示

**配置项**：

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| 服务商 | 下拉选择 | 选择LLM服务商 | 阿里云千问 |
| API Key | 密码输入 | 服务商API密钥 | 从.env加载 |
| 模型名称 | 下拉选择 | 选择具体模型 | qwen-turbo |
| 系统提示词 | 文本域 | 定义Agent行为 | 智能推理助手 |

**功能点**：

| 功能 | 描述 | 输入 | 输出 | 异常处理 |
|------|------|------|------|----------|
| 加载配置 | 页面加载时读取当前配置 | - | 表单预填充 | 配置文件不存在时使用默认值 |
| 保存配置 | 保存表单配置到文件 | 表单数据 | 保存成功提示 | 验证失败时显示错误信息 |
| 测试连接 | 测试当前配置是否有效 | 按钮点击 | 连接成功/失败 | API错误时显示具体错误信息 |

---

## 四、API 接口规格

### 4.1 接口概览

| 接口 | 方法 | 路径 | 描述 |
|------|------|------|------|
| 首页 | GET | `/` | 用户聊天页面 |
| 管理页 | GET | `/admin` | 后台管理页面 |
| 获取配置 | GET | `/api/config` | 获取当前配置 |
| 更新配置 | POST | `/api/config` | 更新配置 |
| 可用模型 | GET | `/api/models` | 获取支持的模型列表 |
| 发起对话 | POST | `/api/chat` | 发起对话请求 |
| 流式输出 | GET | `/api/chat/stream` | SSE流式输出 |

### 4.2 详细接口定义

#### 4.2.1 获取配置 - GET /api/config

**请求**：
```
GET /api/config
```

**响应** (200 OK)：
```json
{
  "success": true,
  "data": {
    "provider": "qwen",
    "api_key": "sk-********",
    "model": "qwen-turbo",
    "system_prompt": "你是一个智能推理助手..."
  }
}
```

#### 4.2.2 更新配置 - POST /api/config

**请求**：
```
POST /api/config
Content-Type: application/json

{
  "provider": "qwen",
  "api_key": "sk-xxx",
  "model": "qwen-turbo",
  "system_prompt": "你是一个智能推理助手..."
}
```

**响应** (200 OK)：
```json
{
  "success": true,
  "message": "配置保存成功"
}
```

**响应** (400 Bad Request)：
```json
{
  "success": false,
  "error": "配置验证失败",
  "details": {
    "api_key": "API Key不能为空"
  }
}
```

#### 4.2.3 获取可用模型 - GET /api/models

**请求**：
```
GET /api/models?provider=qwen
```

**响应** (200 OK)：
```json
{
  "success": true,
  "data": {
    "provider": "qwen",
    "models": [
      {
        "id": "qwen-turbo",
        "name": "千问Turbo",
        "description": "快速推理，适合日常使用"
      },
      {
        "id": "qwen-plus",
        "name": "千问Plus",
        "description": "更强能力，适合复杂任务"
      },
      {
        "id": "qwen-max",
        "name": "千问Max",
        "description": "最强能力，适合专业场景"
      }
    ]
  }
}
```

#### 4.2.4 发起对话 - POST /api/chat

**请求**：
```
POST /api/chat
Content-Type: application/json

{
  "message": "如果5台机器5分钟生产5个零件，那么100台机器生产100个零件需要多长时间？",
  "stream": true
}
```

**响应** (200 OK)：
```json
{
  "success": true,
  "session_id": "sess_abc123",
  "message": "对话已发起，请通过 /api/chat/stream 获取流式输出"
}
```

#### 4.2.5 流式输出 - GET /api/chat/stream

**请求**：
```
GET /api/chat/stream?session_id=sess_abc123
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**SSE事件流格式**：
```
event: data
data: {"type": "text", "content": "你"}

event: data
data: {"type": "text", "content": "好"}

event: data
data: {"type": "text", "content": "，"}

event: done
data: {"type": "done", "usage": {"input_tokens": 10, "output_tokens": 50, "total_tokens": 60}}
```

**事件类型**：

| 事件类型 | 描述 | 数据格式 |
|----------|------|----------|
| `data` | 普通文本内容 | `{"type": "text", "content": "xxx"}` |
| `done` | 输出完成 | `{"type": "done", "usage": {...}}` |
| `error` | 发生错误 | `{"type": "error", "message": "xxx"}` |

---

## 五、数据模型

### 5.1 配置模型 (config.json)

```json
{
  "version": "1.0",
  "updated_at": "2026-04-25T10:30:00Z",
  "current_provider": "qwen",
  "providers": {
    "qwen": {
      "name": "阿里云千问",
      "api_key": "sk-xxx",
      "default_model": "qwen-turbo",
      "available_models": ["qwen-turbo", "qwen-plus", "qwen-max"]
    },
    "openai": {
      "name": "OpenAI",
      "api_key": "",
      "default_model": "gpt-3.5-turbo",
      "available_models": ["gpt-3.5-turbo", "gpt-4"]
    }
  },
  "system_prompt": "你是一个智能推理助手。当用户提出问题时，你需要：\n1. 仔细分析问题\n2. 逐步思考解决方法\n3. 给出最终答案"
}
```

### 5.2 对话消息模型

```json
{
  "id": "msg_abc123",
  "role": "user",
  "content": "用户输入的问题",
  "timestamp": "2026-04-25T10:30:00Z"
}
```

### 5.3 服务商支持列表

| 服务商ID | 服务商名称 | SDK | 支持状态 |
|----------|------------|-----|----------|
| `qwen` | 阿里云千问 | dashscope | ✅ 支持 |
| `openai` | OpenAI | openai | ⏳ 预留接口 |

---

## 六、前端页面规格

### 6.1 页面路由

| 路径 | 页面 | 模板文件 |
|------|------|----------|
| `/` | 用户聊天页 | `templates/index.html` |
| `/admin` | 后台管理页 | `templates/admin.html` |

### 6.2 用户聊天页面设计

#### 颜色方案
- 主色调：蓝色 (#3b82f6) - 代表科技感
- 背景色：浅灰 (#f3f4f6)
- 用户气泡：蓝色背景 (#3b82f6)，白色文字
- 模型气泡：白色背景，深色文字
- 边框：浅灰 (#e5e7eb)

#### 组件布局
```
┌─────────────────────────────────────────────────────┐
│  🤖 Agent 推理助手                          [管理后台] │  ← 导航栏
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │  [模型] 如果5台机器5分钟生产5个零件...        │  │  ← 模型消息
│  └─────────────────────────────────────────────┘  │
│                                                     │
│                        ┌─────────────────────────┐ │
│                        │ 100台机器生产100个零件    │ │  ← 用户消息
│                        │ 需要5分钟。              │ │
│                        └─────────────────────────┘ │
│                                                     │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐ [发送] │  ← 输入区域
│  │  输入你的问题...                          │       │
│  └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### 6.3 后台管理页面设计

#### 表单布局
```
┌─────────────────────────────────────────────────────┐
│  ⚙️ 后台管理                              [返回首页] │  ← 导航栏
├─────────────────────────────────────────────────────┤
│                                                     │
│  服务商配置                                          │
│  ┌─────────────────────────────────────────────┐  │
│  │  服务商: [阿里云千问 ▼]                        │  │
│  │  API Key: [***********] [显示/隐藏]           │  │
│  │  模型: [qwen-turbo ▼]                         │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  系统提示词                                          │
│  ┌─────────────────────────────────────────────┐  │
│  │  你是一个智能推理助手...                        │  │
│  │  (可调整大小的文本域)                           │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  [测试连接]                              [保存配置]  │  ← 操作按钮
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 七、错误处理规格

### 7.1 错误类型

| 错误类型 | HTTP状态码 | 场景 |
|----------|------------|------|
| 配置错误 | 400 | API Key缺失、模型不存在 |
| 认证错误 | 401 | API Key无效 |
| 服务错误 | 500 | 模型服务不可用 |
| 网络错误 | 503 | 网络连接失败 |

### 7.2 错误响应格式

```json
{
  "success": false,
  "error_code": "AUTH_FAILED",
  "error_message": "API Key认证失败，请检查配置",
  "details": {
    "provider": "qwen",
    "model": "qwen-turbo"
  }
}
```

### 7.3 前端错误提示

- **用户可见错误**：使用Toast提示框显示
- **技术错误**：记录到控制台，不直接展示给用户
- **流式中断**：显示"连接已断开"，提供重试按钮

---

## 八、安全性规格

### 8.1 敏感信息处理

| 敏感信息 | 存储方式 | 传输方式 | 前端展示 |
|----------|----------|----------|----------|
| API Key | 加密存储 (Base64) | HTTPS | 掩码显示 (sk-******) |
| 对话内容 | 内存存储 | HTTPS | 明文显示 |

### 8.2 安全措施

1. **API Key不硬编码**：通过.env或配置文件管理
2. **配置文件.gitignore**：.env和data/config.json不提交到Git
3. **前端掩码显示**：API Key只显示前几位和后几位
4. **后端验证**：所有配置更新都经过后端验证

---

## 九、测试规格

### 9.1 测试场景

#### 单元测试
- [ ] 配置加载和保存
- [ ] API Key验证
- [ ] 服务商切换

#### 集成测试
- [ ] 完整对话流程
- [ ] 流式输出接收
- [ ] 配置更新生效

#### 手动测试用例

| 用例ID | 用例描述 | 前置条件 | 操作步骤 | 预期结果 |
|--------|----------|----------|----------|----------|
| TC001 | 发送空消息 | 页面已加载 | 1. 不输入内容<br>2. 点击发送 | 提示"请输入问题" |
| TC002 | 正常对话 | 配置正确 | 1. 输入问题<br>2. 点击发送 | 流式显示响应 |
| TC003 | 切换服务商 | 管理页已打开 | 1. 选择OpenAI<br>2. 保存配置 | 配置保存成功 |
| TC004 | 无效API Key | 配置错误API Key | 1. 保存配置<br>2. 发起对话 | 提示认证失败 |

---

## 十、开发任务清单

### 阶段一：后端基础 (优先级P0)

- [x] 10.1 创建项目目录结构
- [x] 10.2 实现配置管理模块 (config.py)
- [ ] 10.3 实现LLM Agent接口 (agents/llm_agent.py)
- [ ] 10.4 实现Flask路由和API接口 (app.py)
- [ ] 10.5 实现SSE流式输出

### 阶段二：前端开发 (优先级P0)

- [ ] 20.1 创建用户聊天页面 (templates/index.html)
- [ ] 20.2 实现前端聊天逻辑 (static/js/chat.js)
- [ ] 20.3 创建后台管理页面 (templates/admin.html)
- [ ] 20.4 实现后台管理逻辑 (static/js/admin.js)

### 阶段三：集成与测试 (优先级P1)

- [ ] 30.1 端到端集成测试
- [ ] 30.2 错误处理优化
- [ ] 30.3 代码Review和重构

---

## 十一、变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-04-25 | 初始版本，定义完整规格 | AI Assistant |

---

## 十二、附录

### 12.1 参考资料
- [Flask官方文档](https://flask.palletsprojects.com/)
- [Server-Sent Events (SSE)规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [阿里云DashScope SDK文档](https://help.aliyun.com/zh/dashscope/)
- [Tailwind CSS文档](https://tailwindcss.com/docs)

### 12.2 术语表

| 术语 | 定义 |
|------|------|
| Agent | 智能体，具备推理、行动、记忆、规划能力的AI系统 |
| SSE | Server-Sent Events，服务器向客户端单向推送数据的技术 |
| 流式输出 | 模型逐字生成响应并实时返回给客户端 |
| 服务商 | 提供LLM服务的厂商（如阿里云、OpenAI） |

---

---

## 十四、工具调用功能规格 (新增)

### 14.1 功能背景

当前系统只能调用大模型进行推理，但对于时效性强的问题（如新闻、天气、实时数据等），模型的知识截止日期限制导致回答质量不佳。需要添加工具调用能力，让模型能够：

1. **网络搜索**：获取实时新闻、最新信息
2. **扩展能力**：未来可支持更多工具（天气、计算器、文件操作等）

### 14.2 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户提问                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLM 推理 + 工具判断                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  系统提示词："根据问题判断是否需要调用工具..."           │   │
│  │  工具定义：[{name, description, parameters}]         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  直接回答       │    │  调用网络搜索   │    │  调用其他工具   │
│  (不需要工具)   │    │  (web_search) │    │  (未来扩展)    │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   工具结果返回给 LLM                           │
│         LLM 根据工具返回结果生成最终回答                       │
└─────────────────────────────────────────────────────────────┘
```

### 14.3 工具模块设计

#### 14.3.1 目录结构
```
agents/
├── __init__.py
├── llm_agent.py          # 现有LLM调用
├── tools/
│   ├── __init__.py
│   ├── base_tool.py      # 工具基类
│   ├── tool_manager.py   # 工具管理器
│   └── web_search_tool.py # 网络搜索工具
└── agent_with_tools.py   # 带工具能力的Agent
```

#### 14.3.2 工具基类 (BaseTool)
```python
@dataclass
class ToolResult:
    success: bool
    content: str
    error: Optional[str] = None

class BaseTool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema格式
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
    
    def to_function_def(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
```

#### 14.3.3 工具管理器 (ToolManager)
- 注册和管理所有可用工具
- 提供工具定义列表给LLM
- 解析LLM的工具调用请求并执行

#### 14.3.4 网络搜索工具 (WebSearchTool)
**功能**：使用搜索引擎获取实时信息

**参数定义**：
```python
{
    "name": "web_search",
    "description": "在互联网上搜索最新的实时信息。用于回答时效性强的问题，如：新闻、天气、体育赛事、当前事件等。当问题涉及'最新'、'今天'、'现在'等时效性词汇时，应使用此工具。",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询关键词，应该简洁明了"
            },
            "num_results": {
                "type": "integer",
                "description": "返回结果数量，默认5条，最多10条",
                "default": 5
            }
        },
        "required": ["query"]
    }
}
```

**实现方式**：使用 `WebSearch` 工具进行网络搜索

### 14.4 LLM Agent 工具调用流程

#### 14.4.1 ReAct 模式流程
```
1. 用户输入问题
   ↓
2. LLM 判断：是否需要调用工具？
   ├─ 否：直接生成回答 → 返回给用户
   └─ 是：生成工具调用请求
           ↓
3. 执行工具，获取结果
   ↓
4. 将工具结果加入对话历史
   ↓
5. LLM 根据结果生成最终回答
   ↓
6. 返回给用户
```

#### 14.4.2 消息格式扩展
支持 `tool_calls` 和 `tool_response` 消息类型：

```python
# 工具调用请求（LLM返回）
{
    "role": "assistant",
    "content": null,
    "tool_calls": [
        {
            "id": "call_xxx",
            "type": "function",
            "function": {
                "name": "web_search",
                "arguments": "{\"query\": \"2026年最新科技新闻\"}"
            }
        }
    ]
}

# 工具响应（返回给LLM）
{
    "role": "tool",
    "tool_call_id": "call_xxx",
    "content": "[搜索结果JSON]"
}
```

### 14.5 系统提示词更新

**新的系统提示词模板**：
```
你是一个智能推理助手，可以使用工具来获取实时信息。

可用工具：
{tools_list}

使用规则：
1. 对于时效性问题（如新闻、天气、实时数据），请先使用 web_search 工具
2. 对于常识性问题，可以直接回答
3. 调用工具时，请严格按照工具参数要求传递参数
4. 工具返回结果后，根据结果生成最终回答

回答风格：
- 简洁明了
- 逻辑清晰
- 如果使用了工具，请在回答开头注明"[已搜索]"
```

### 14.6 API 接口更新

#### 14.6.1 流式输出事件扩展

新增事件类型：

| 事件类型 | 描述 | 数据格式 |
|----------|------|----------|
| `tool_call` | 模型决定调用工具 | `{"type": "tool_call", "tool": "web_search", "query": "xxx"}` |
| `tool_result` | 工具执行完成 | `{"type": "tool_result", "tool": "web_search", "success": true}` |
| `text` | 普通文本内容（原有） | `{"type": "text", "content": "xxx"}` |
| `done` | 输出完成（原有） | `{"type": "done", "usage": {...}}` |

**SSE 事件流示例**：
```
event: data
data: {"type": "tool_call", "tool": "web_search", "query": "2026年最新AI新闻"}

event: data
data: {"type": "tool_result", "tool": "web_search", "success": true, "result_count": 5}

event: data
data: {"type": "text", "content": "根"}

event: data
data: {"type": "text", "content": "据"}

event: data
data: {"type": "text", "content": "搜"}

event: data
data: {"type": "text", "content": "索"}

event: data
data: {"type": "text", "content": "结"}

event: data
data: {"type": "text", "content": "果"}

event: data
data: {"type": "done", "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}
```

### 14.7 前端展示更新

#### 14.7.1 工具调用可视化

在消息气泡中添加工具调用状态展示：

```
┌─────────────────────────────────────────────────────────┐
│ 🤖 Agent                                                 │
├─────────────────────────────────────────────────────────┤
│ 🔍 正在搜索: "2026年最新AI新闻"...                      │  ← 工具调用中
├─────────────────────────────────────────────────────────┤
│ ✅ 搜索完成，找到 5 条结果                               │  ← 工具完成
├─────────────────────────────────────────────────────────┤
│ 根据搜索结果，2026年AI领域的最新进展包括：               │  ← 最终回答
│ 1. 多模态模型能力大幅提升...                             │
│ 2. 自动驾驶技术商业化加速...                             │
└─────────────────────────────────────────────────────────┘
```

#### 14.7.2 交互逻辑更新

- 收到 `tool_call` 事件：显示"正在调用工具"动画
- 收到 `tool_result` 事件：显示工具执行结果摘要
- 收到 `text` 事件：逐字显示最终回答（原有逻辑）

### 14.8 开发任务清单 (工具调用功能)

#### 阶段一：工具框架搭建 (P0)
- [ ] 14.8.1 创建 `agents/tools/` 目录结构
- [ ] 14.8.2 实现 `BaseTool` 抽象基类
- [ ] 14.8.3 实现 `ToolManager` 工具管理器
- [ ] 14.8.4 实现 `AgentWithTools` 带工具能力的Agent

#### 阶段二：网络搜索工具实现 (P0)
- [ ] 14.8.5 实现 `WebSearchTool` 网络搜索工具
- [ ] 14.8.6 集成搜索结果格式化

#### 阶段三：LLM Agent 集成 (P0)
- [ ] 14.8.7 修改 `llm_agent.py` 支持 tools 参数
- [ ] 14.8.8 实现 ReAct 循环逻辑
- [ ] 14.8.9 更新系统提示词模板

#### 阶段四：API 和前端更新 (P1)
- [ ] 14.8.10 后端API支持工具调用事件
- [ ] 14.8.11 前端展示工具调用过程
- [ ] 14.8.12 添加工具调用日志

---

## 十五、评审检查清单 (三轴评审 - 更新版)

### 15.1 功能轴 (正确性)
- [x] 所有API接口符合规格定义
- [x] 流式输出正常工作
- [x] 配置保存和加载正确
- [x] 错误处理符合规格
- [ ] 工具框架可正常注册和管理工具
- [ ] LLM能正确判断何时需要调用工具
- [ ] 网络搜索工具能返回有效结果
- [ ] ReAct循环逻辑正确执行

### 15.2 体验轴 (可用性)
- [x] 页面布局美观、响应式
- [x] 流式输出流畅，打字机效果自然
- [x] 错误提示清晰、友好
- [x] 操作流程直观、简单
- [ ] 工具调用过程可视化
- [ ] 工具执行结果清晰展示
- [ ] 整体回答流程流畅自然

### 15.3 代码轴 (可维护性)
- [x] 代码结构清晰，模块化
- [x] 命名规范、有意义
- [x] 关键逻辑有注释
- [x] 无硬编码的敏感信息
- [ ] 工具模块遵循开闭原则（可扩展）
- [ ] 工具定义与实现分离
- [ ] 错误处理完善

---

**文档状态**：✅ 规格说明已更新，包含工具调用功能
**下一步**：开始实现工具调用功能代码

---

## 十六、流式输出与推理过程可视化优化规格 (新增 v1.1.0)

### 16.1 问题背景

当前实现存在两个关键问题：

#### 问题1：伪流式输出
**当前实现**：
```python
# app.py 中的当前逻辑
result = agent.chat(...)  # 同步执行，等待整个过程完成

# 然后批量输出所有事件
for event in events:
    yield event
    
# 再逐个输出最终答案的字符
for char in result.final_answer:
    yield text_event
```

**问题**：
- 用户需要等待整个过程完成才能看到任何内容
- 工具调用过程无法实时展示
- 用户体验差，感觉像是"卡住了"

#### 问题2：推理过程不透明
**当前实现**：
- 只展示了工具调用的最终状态
- 没有展示 LLM 的思考过程
- 没有展示 Agent 的规划过程
- 用户无法判断答案是否基于真实搜索

**用户诉求**：
> "有些信息看起来不像是真实的，又无法判断是不是调用工具的结果"

### 16.2 优化目标

1. **真正的流式输出**：执行过程中实时推送事件
2. **推理过程可视化**：展示完整的思考链（类似 ChatGPT 的思考过程）
3. **用户可验证**：明确展示哪些部分基于工具调用结果

### 16.3 事件类型扩展

#### 16.3.1 新增事件类型

| 事件类型 | 触发时机 | 描述 | 数据格式 |
|----------|----------|------|----------|
| `thinking` | LLM 开始推理时 | LLM 正在分析问题、判断是否需要工具 | `{"type": "thinking", "content": "正在分析问题..."}` |
| `reasoning` | LLM 进行推理时 | LLM 的推理内容（如果支持流式 reasoning） | `{"type": "reasoning", "content": "推理内容..."}` |
| `planning` | LLM 决定调用工具前 | LLM 决定需要调用工具，并规划如何调用 | `{"type": "planning", "content": "需要搜索最新信息...", "tool": "web_search"}` |
| `tool_call` | 实际调用工具时 | 工具正在执行 | `{"type": "tool_call", "tool": "web_search", "query": "xxx"}` |
| `tool_result` | 工具执行完成时 | 工具返回结果 | `{"type": "tool_result", "tool": "web_search", "success": true, "result_count": 5}` |
| `text` | 输出最终答案时 | 最终答案的字符（流式） | `{"type": "text", "content": "x"}` |
| `done` | 整个过程完成时 | 完成标志，包含 Token 使用统计 | `{"type": "done", "usage": {...}}` |

#### 16.3.2 事件流示例

**场景：需要调用工具的问题**

```
event: data
data: {"type": "thinking", "content": "正在分析问题..."}

event: data
data: {"type": "planning", "content": "这个问题涉及实时信息，需要使用 web_search 工具搜索最新信息。", "tool": "web_search"}

event: data
data: {"type": "tool_call", "tool": "web_search", "query": "2026年AI大模型最新新闻"}

event: data
data: {"type": "tool_result", "tool": "web_search", "success": true, "result_count": 5}

event: data
data: {"type": "thinking", "content": "正在根据搜索结果生成回答..."}

event: data
data: {"type": "text", "content": "根"}

event: data
data: {"type": "text", "content": "据"}

event: data
data: {"type": "text", "content": "搜"}

event: data
data: {"type": "text", "content": "索"}

...

event: data
data: {"type": "done", "usage": {"input_tokens": 500, "output_tokens": 200, "total_tokens": 700}}
```

**场景：不需要调用工具的问题**

```
event: data
data: {"type": "thinking", "content": "正在分析问题..."}

event: data
data: {"type": "planning", "content": "这是一个常识性问题，可以直接回答。"}

event: data
data: {"type": "text", "content": "你"}

event: data
data: {"type": "text", "content": "好"}

...

event: data
data: {"type": "done", "usage": {...}}
```

### 16.4 后端实现规格

#### 16.4.1 数据流架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户请求                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AgentWithTools.chat_stream()                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. 发送 "thinking" 事件                                   │   │
│  │  2. LLM 第一次调用（判断是否需要工具）                      │   │
│  │  3. 发送 "planning" 事件（LLM 的决策）                     │   │
│  │  4. 如果需要工具：                                          │   │
│  │     ├─ 发送 "tool_call" 事件                               │   │
│  │     ├─ 执行工具                                             │   │
│  │     └─ 发送 "tool_result" 事件                             │   │
│  │  5. LLM 第二次调用（根据工具结果生成回答）                   │   │
│  │  6. 流式发送 "text" 事件（最终答案）                        │   │
│  │  7. 发送 "done" 事件                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SSE 实时推送事件                              │
└─────────────────────────────────────────────────────────────────┘
```

#### 16.4.2 核心接口设计

**AgentWithTools.chat_stream()**

```python
@dataclass
class StreamEvent:
    """流式事件"""
    event_type: str  # thinking, planning, tool_call, tool_result, text, done
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentWithTools:
    # ...
    
    def chat_stream(
        self,
        user_message: str,
        history: List[ChatMessage] = None
    ) -> Generator[StreamEvent, None, None]:
        """
        流式对话，实时推送事件
        
        Yields:
            StreamEvent: 各个阶段的事件
        """
        messages = history.copy() if history else []
        messages.append(ChatMessage(role="user", content=user_message))
        
        # 1. 发送 thinking 事件
        yield StreamEvent(
            event_type="thinking",
            content="正在分析问题..."
        )
        
        # 2. LLM 第一次调用：判断是否需要工具
        result = self.llm_service.chat(
            messages=messages,
            tools=self.tool_manager.get_tools_definition()
        )
        
        # 3. 发送 planning 事件
        if result.tool_calls:
            yield StreamEvent(
                event_type="planning",
                content="需要使用工具获取实时信息...",
                metadata={"tool": result.tool_calls[0].get("function", {}).get("name")}
            )
            
            # 4. 执行工具调用
            for tool_call_data in result.tool_calls:
                # 发送 tool_call 事件
                tool_name = tool_call_data.get("function", {}).get("name")
                args = json.loads(tool_call_data.get("function", {}).get("arguments", "{}"))
                
                yield StreamEvent(
                    event_type="tool_call",
                    content=f"正在调用 {tool_name}...",
                    metadata={"tool": tool_name, "query": args.get("query", "")}
                )
                
                # 执行工具
                tool_result = self.tool_manager.execute_tool(tool_name, **args)
                
                # 发送 tool_result 事件
                yield StreamEvent(
                    event_type="tool_result",
                    content=f"{tool_name} 执行完成",
                    metadata={
                        "tool": tool_name,
                        "success": tool_result.success,
                        "result_count": len(tool_result.metadata.get("results", []))
                    }
                )
                
                # 添加工具消息到历史
                tool_msg = ChatMessage(
                    role="tool",
                    content=tool_result.content if tool_result.success else json.dumps({"error": tool_result.error}),
                    tool_call_id=tool_call_data.get("id"),
                    name=tool_name
                )
                messages.append(tool_msg)
            
            # 5. 发送 thinking 事件（准备生成最终答案）
            yield StreamEvent(
                event_type="thinking",
                content="正在根据搜索结果生成回答..."
            )
            
            # 6. LLM 第二次调用：流式生成最终答案
            for chunk in self.llm_service.chat_stream(
                messages=messages
            ):
                if chunk.content:
                    yield StreamEvent(
                        event_type="text",
                        content=chunk.content
                    )
        else:
            # 不需要工具，直接流式生成回答
            yield StreamEvent(
                event_type="planning",
                content="这是一个常识性问题，可以直接回答。"
            )
            
            for chunk in self.llm_service.chat_stream(
                messages=messages
            ):
                if chunk.content:
                    yield StreamEvent(
                        event_type="text",
                        content=chunk.content
                    )
        
        # 7. 发送 done 事件
        yield StreamEvent(
            event_type="done",
            content="",
            metadata={"usage": total_usage}
        )
```

### 16.5 前端展示规格

#### 16.5.1 UI 设计

**整体布局**：

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Agent 推理助手                                        [管理后台]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [用户] 搜索2026年AI大模型最新新闻                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🤖 Agent                                                 │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 💭 正在分析问题...                                │    │   │  ← thinking
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 📋 规划：这个问题涉及实时信息，需要搜索最新数据    │    │   │  ← planning
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 🔍 正在搜索: "2026年AI大模型最新新闻"...         │    │   │  ← tool_call
│  │  │    (加载动画)                                      │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ✅ 搜索完成，找到 5 条结果                        │    │   │  ← tool_result
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 💭 正在根据搜索结果生成回答...                     │    │   │  ← thinking
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ───────────────────────────────────────────────────    │   │  ← 分隔线
│  │  根据搜索结果，2026年AI领域的最新进展包括：             │    │   │
│  │  1. 多模态模型能力大幅提升...                           │    │   │  ← 最终答案
│  │  2. 自动驾驶技术商业化加速...                           │    │   │     (流式显示)
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐ [发送]   │
│  │  输入你的问题...                                  │         │
│  └─────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

#### 16.5.2 事件处理逻辑

```javascript
class ChatApp {
    // ...
    
    handleEvent(event) {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
            case 'thinking':
                this.showThinking(data.content);
                break;
                
            case 'planning':
                this.showPlanning(data.content, data.tool);
                break;
                
            case 'tool_call':
                this.showToolCall(data.tool, data.query);
                break;
                
            case 'tool_result':
                this.showToolResult(data.tool, data.success, data.result_count);
                break;
                
            case 'text':
                this.appendToAnswer(data.content);
                break;
                
            case 'done':
                this.showComplete(data.usage);
                break;
                
            case 'error':
                this.showError(data.content);
                break;
        }
    }
    
    showThinking(content) {
        // 添加思考状态，使用柔和的动画
        const thinkingEl = this.createThinkingElement(content);
        thinkingEl.style.opacity = '0.8';
        this.assistantMessageEl.appendChild(thinkingEl);
    }
    
    showPlanning(content, tool) {
        // 展示规划内容，可展开查看详细推理
        const planningEl = this.createPlanningElement(content, tool);
        this.assistantMessageEl.appendChild(planningEl);
    }
    
    showToolCall(tool, query) {
        // 展示工具调用，带加载动画
        const toolCallEl = this.createToolCallElement(tool, query);
        this.assistantMessageEl.appendChild(toolCallEl);
        toolCallEl.querySelector('.loading-icon').classList.add('spin');
    }
    
    showToolResult(tool, success, resultCount) {
        // 更新工具调用状态为完成
        const toolResultEl = this.updateToolCallToComplete(tool, success, resultCount);
        // 添加分隔线
        this.addSeparator();
    }
    
    appendToAnswer(content) {
        // 流式追加到最终答案
        this.finalAnswerEl.textContent += content;
    }
}
```

#### 16.5.3 样式规格

**颜色方案**：
- thinking: 浅灰背景 (#f3f4f6)，灰色文字
- planning: 浅蓝背景 (#eff6ff)，蓝色文字
- tool_call: 浅黄背景 (#fffbeb)，橙色文字 + 加载动画
- tool_result: 浅绿背景 (#f0fdf4)，绿色文字
- text: 正常文字颜色

**动画效果**：
- thinking: 淡入淡出
- tool_call: 加载旋转动画
- 状态切换: 平滑过渡

### 16.6 关键实现点

#### 16.6.1 真正的流式输出

**核心改动**：
1. `AgentWithTools.chat()` 改为生成器模式，实时 yield 事件
2. `app.py` 中的 `chat_stream()` 直接转发事件，不再等待整个过程完成
3. LLM 服务需要支持真正的流式调用

**代码模式**：
```python
# 之前的方式（伪流式）
def chat_stream():
    result = agent.chat(...)  # 阻塞等待
    for event in events:       # 批量输出
        yield event

# 新的方式（真正流式）
def chat_stream():
    for event in agent.chat_stream(...):  # 实时获取
        yield event                          # 实时输出
```

#### 16.6.2 推理过程可验证

**实现要点**：
1. 每个事件都有明确的类型和内容
2. 工具调用过程清晰可见（调用了什么工具、参数是什么、结果如何）
3. 最终答案与工具调用之间有明确的分隔
4. 用户可以清楚地看到：答案是否基于工具调用结果

### 16.7 开发任务清单

#### 阶段一：后端流式输出改造 (P0)
- [ ] 16.7.1 实现 `AgentWithTools.chat_stream()` 生成器方法
- [ ] 16.7.2 实现 `StreamEvent` 数据类
- [ ] 16.7.3 修改 `app.py` 的 `chat_stream()` 支持真正流式
- [ ] 16.7.4 确保 LLM 服务支持流式调用

#### 阶段二：推理过程可视化 (P0)
- [ ] 16.7.5 新增事件类型：thinking, planning
- [ ] 16.7.6 优化 tool_call, tool_result 事件
- [ ] 16.7.7 前端处理新事件类型
- [ ] 16.7.8 设计并实现思考链 UI

#### 阶段三：用户体验优化 (P1)
- [ ] 16.7.9 添加动画和过渡效果
- [ ] 16.7.10 优化移动端布局
- [ ] 16.7.11 添加思考过程可折叠/展开功能

### 16.8 验收标准

#### 功能验收
- [ ] 用户输入问题后，立即看到 "正在分析问题..."
- [ ] 工具调用过程实时展示（调用什么工具、参数是什么）
- [ ] 工具执行结果实时展示（成功/失败、结果数量）
- [ ] 最终答案逐字流式显示
- [ ] 整个过程没有明显的"卡顿"感

#### 体验验收
- [ ] 用户能清楚地看到：Agent 在思考什么
- [ ] 用户能清楚地看到：Agent 调用了什么工具
- [ ] 用户能清楚地看到：答案是否基于搜索结果
- [ ] 整体流程流畅自然，类似 ChatGPT 的体验

#### 代码验收
- [ ] 后端使用真正的生成器模式
- [ ] 事件类型定义清晰，易于扩展
- [ ] 前端事件处理模块化
- [ ] 代码注释完整

---

**文档状态**：✅ 优化规格已定义
**下一步**：开始实现流式输出和推理过程可视化
