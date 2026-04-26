# 记忆功能模块架构规划文档

**版本**: v1.2.0
**日期**: 2026-04-26
**状态**: 开发中
**作者**: AI Assistant

---

## 一、问题背景

### 1.1 当前系统状态

| 维度 | 当前状态 | 问题 |
|------|----------|------|
| **对话存储** | 前端内存 (`this.messages`) | 刷新页面丢失，无持久化 |
| **后端状态** | 无状态（stateless） | 每次请求独立，无上下文关联 |
| **会话管理** | 无 | 无法管理多个对话 |
| **长期记忆** | 无 | 无法记住用户偏好、历史知识 |
| **记忆检索** | 无 | 无法根据历史对话回答问题 |

### 1.2 用户痛点

1. **对话丢失**：刷新浏览器后，所有对话历史消失
2. **无法多任务**：一次只能进行一个对话，无法切换不同主题
3. **无上下文延续**：每次对话都是新的，无法记住之前说过什么
4. **无法学习**：系统无法从历史对话中学习用户偏好

---

## 二、记忆功能架构

### 2.1 记忆层次模型

参考人类记忆系统，设计三层记忆架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                        记忆层次模型                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    短期记忆 (Short-term)                 │   │
│  │  - 当前会话的所有消息                                     │   │
│  │  - 用于实时推理上下文                                      │   │
│  │  - 存活时间：当前会话期间                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    工作记忆 (Working)                    │   │
│  │  - 从对话中提取的关键信息                                 │   │
│  │  - 用户当前任务状态                                       │   │
│  │  - 工具调用的中间结果                                     │   │
│  │  - 存活时间：会话结束后可选择保存                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    长期记忆 (Long-term)                  │   │
│  │  - 所有历史对话摘要                                       │   │
│  │  - 用户偏好、个人信息                                     │   │
│  │  - 从对话中学习的知识                                     │   │
│  │  - 存活时间：永久（可手动删除）                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      记忆模块技术架构                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   前端 UI    │    │  Flask API   │    │  Agent 流程  │    │
│  │  (chat.js)  │◄──►│   (app.py)   │◄──►│ (llm_agent)  │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MemoryManager (记忆管理器)                   │   │
│  │  - 会话管理 (创建/切换/删除/重命名)                       │   │
│  │  - 消息存储 (保存/加载/删除)                              │   │
│  │  - 记忆检索 (根据问题检索相关历史)                        │   │
│  │  - 记忆总结 (生成对话摘要)                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MemoryStore (存储层)                         │   │
│  │  - SQLite 数据库 (会话、消息、摘要)                       │   │
│  │  - 可扩展：向量存储 (语义检索)                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、数据模型设计

### 3.1 数据库表结构

#### 表1：sessions（会话表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | TEXT | PRIMARY KEY | 会话唯一标识（UUID） |
| title | TEXT | NOT NULL | 会话标题（用户可见） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 最后更新时间 |
| is_active | INTEGER | DEFAULT 1 | 是否活跃 |
| metadata | TEXT | - | 扩展元数据（JSON格式） |

#### 表2：messages（消息表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | TEXT | PRIMARY KEY | 消息唯一标识 |
| session_id | TEXT | FOREIGN KEY | 所属会话ID |
| role | TEXT | NOT NULL | 角色：user/assistant/tool/system |
| content | TEXT | - | 消息内容 |
| tool_calls | TEXT | - | 工具调用信息（JSON） |
| tool_call_id | TEXT | - | 工具调用ID（用于tool角色） |
| tool_name | TEXT | - | 工具名称 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| metadata | TEXT | - | 元数据（token使用等） |

#### 表3：memory_summaries（记忆摘要表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | TEXT | PRIMARY KEY | 摘要唯一标识 |
| session_id | TEXT | FOREIGN KEY | 所属会话ID |
| summary_type | TEXT | NOT NULL | 摘要类型：session/key_point/fact |
| content | TEXT | NOT NULL | 摘要内容 |
| importance | INTEGER | DEFAULT 5 | 重要程度（1-10） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| source_message_ids | TEXT | - | 来源消息ID列表（JSON） |

### 3.2 数据模型类定义

```python
@dataclass
class Session:
    """会话数据模型"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """消息数据模型"""
    id: str
    session_id: str
    role: str  # user, assistant, tool, system
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_chat_message(self) -> ChatMessage:
        """转换为LLM使用的ChatMessage格式"""
        return ChatMessage(
            role=self.role,
            content=self.content,
            tool_calls=self.tool_calls,
            tool_call_id=self.tool_call_id,
            name=self.tool_name
        )


@dataclass
class MemorySummary:
    """记忆摘要数据模型"""
    id: str
    session_id: str
    summary_type: str  # session, key_point, fact
    content: str
    importance: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    source_message_ids: List[str] = field(default_factory=list)
```

---

## 四、核心功能设计

### 4.1 会话管理功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 创建会话 | 用户开始新对话时自动创建 | P0 |
| 切换会话 | 从会话列表选择历史对话继续 | P0 |
| 删除会话 | 删除不需要的历史对话 | P0 |
| 重命名会话 | 修改会话标题（更有意义的名称） | P1 |
| 会话列表 | 展示所有历史会话（按时间排序） | P0 |

### 4.2 记忆存储功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 消息持久化 | 每条消息实时保存到数据库 | P0 |
| 会话上下文加载 | 切换会话时加载历史消息 | P0 |
| 消息删除 | 支持删除单条或多条消息 | P2 |

### 4.3 记忆检索功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 上下文加载 | 加载当前会话最近N条消息 | P0 |
| 关键词检索 | 在历史消息中搜索关键词 | P1 |
| 时间过滤 | 按时间范围检索历史 | P1 |
| 相关历史检索 | 根据当前问题检索相关历史对话 | P2 |

### 4.4 记忆总结功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 自动摘要 | 会话结束时自动生成摘要 | P1 |
| 关键事实提取 | 从对话中提取重要事实 | P1 |
| 用户画像构建 | 学习用户偏好、语言风格 | P2 |

---

## 五、API 接口设计

### 5.1 会话管理接口

#### 1. 获取会话列表
```
GET /api/sessions
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "id": "sess_abc123",
      "title": "关于Python编程的讨论",
      "created_at": "2026-04-26T10:30:00Z",
      "updated_at": "2026-04-26T11:00:00Z",
      "message_count": 15
    }
  ]
}
```

#### 2. 创建新会话
```
POST /api/sessions
```

**请求体**：
```json
{
  "title": "新对话"
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "id": "sess_new_123",
    "title": "新对话",
    "created_at": "2026-04-26T12:00:00Z",
    "updated_at": "2026-04-26T12:00:00Z"
  }
}
```

#### 3. 获取会话详情
```
GET /api/sessions/{session_id}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "id": "sess_abc123",
    "title": "关于Python编程的讨论",
    "created_at": "2026-04-26T10:30:00Z",
    "updated_at": "2026-04-26T11:00:00Z",
    "messages": [
      {
        "id": "msg_1",
        "role": "user",
        "content": "什么是Python的装饰器？",
        "created_at": "2026-04-26T10:30:00Z"
      },
      {
        "id": "msg_2",
        "role": "assistant",
        "content": "装饰器是Python中一种强大的功能...",
        "created_at": "2026-04-26T10:31:00Z"
      }
    ]
  }
}
```

#### 4. 更新会话
```
PUT /api/sessions/{session_id}
```

**请求体**：
```json
{
  "title": "Python装饰器详解"
}
```

#### 5. 删除会话
```
DELETE /api/sessions/{session_id}
```

### 5.2 聊天接口更新

**发起对话（支持会话）**
```
POST /api/chat
```

**请求体**：
```json
{
  "message": "用户输入的问题",
  "session_id": "sess_abc123",
  "stream": true
}
```

**说明**：
- 如果提供 `session_id`，则在该会话中继续对话
- 如果不提供 `session_id`，则创建新会话

---

## 六、核心模块设计

### 6.1 MemoryStore（存储层）

```python
class MemoryStore:
    """
    记忆存储层
    封装 SQLite 数据库操作
    """
    
    def __init__(self, db_path: str = None):
        """初始化数据库连接"""
        self.db_path = db_path or self._get_default_path()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        # 创建 sessions, messages, memory_summaries 表
        pass
    
    # 会话操作
    def create_session(self, title: str = "新对话") -> Session:
        """创建新会话"""
        pass
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        pass
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话"""
        pass
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话（级联删除消息）"""
        pass
    
    def list_sessions(self, limit: int = 50) -> List[Session]:
        """获取会话列表（按更新时间倒序）"""
        pass
    
    # 消息操作
    def add_message(self, message: Message) -> bool:
        """添加消息"""
        pass
    
    def add_messages(self, messages: List[Message]) -> bool:
        """批量添加消息"""
        pass
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[Message]:
        """获取会话消息"""
        pass
    
    def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        pass
    
    # 记忆摘要操作
    def add_summary(self, summary: MemorySummary) -> bool:
        """添加记忆摘要"""
        pass
    
    def search_summaries(self, query: str, limit: int = 10) -> List[MemorySummary]:
        """搜索相关摘要"""
        pass
```

### 6.2 MemoryManager（记忆管理器）

```python
class MemoryManager:
    """
    记忆管理器
    提供高层记忆操作接口，整合存储和检索
    """
    
    def __init__(self, store: MemoryStore = None):
        self.store = store or MemoryStore()
    
    # 会话管理
    def create_session(self, title: str = "新对话") -> Session:
        """创建新会话"""
        pass
    
    def get_or_create_session(self, session_id: str = None) -> Session:
        """获取或创建会话"""
        pass
    
    def switch_session(self, session_id: str) -> Tuple[Session, List[Message]]:
        """切换会话，返回会话和历史消息"""
        pass
    
    # 消息管理
    def save_message(self, session_id: str, role: str, content: str, **kwargs) -> Message:
        """保存单条消息"""
        pass
    
    def save_user_message(self, session_id: str, content: str) -> Message:
        """保存用户消息"""
        pass
    
    def save_assistant_message(self, session_id: str, content: str, 
                                tool_calls: List = None, 
                                usage: Dict = None) -> Message:
        """保存助手消息"""
        pass
    
    def save_tool_message(self, session_id: str, tool_call_id: str,
                          tool_name: str, content: str) -> Message:
        """保存工具消息"""
        pass
    
    # 上下文加载
    def get_context(self, session_id: str, 
                    max_messages: int = 20,
                    max_tokens: int = 4000) -> List[ChatMessage]:
        """
        获取对话上下文
        用于传递给LLM进行推理
        """
        pass
```

---

## 七、开发任务清单

### 阶段一：基础存储层 (P0)

- [x] 7.1.1 创建 `agents/memory/` 目录结构
- [x] 7.1.2 实现数据模型类 (`models.py`)
- [x] 7.1.3 实现 `MemoryStore` 存储层
- [x] 7.1.4 数据库表初始化和迁移
- [ ] 7.1.5 编写单元测试

### 阶段二：记忆管理器 (P0)

- [x] 7.2.1 实现 `MemoryManager` 记忆管理器
- [x] 7.2.2 实现会话管理功能
- [x] 7.2.3 实现消息保存和加载
- [x] 7.2.4 实现上下文加载逻辑
- [ ] 7.2.5 编写单元测试

### 阶段三：后端API集成 (P0)

- [x] 7.3.1 添加会话管理API接口
- [x] 7.3.2 修改 `/api/chat` 支持 `session_id` 参数
- [x] 7.3.3 消息发送后自动保存到数据库
- [x] 7.3.4 切换会话时加载历史消息
- [ ] 7.3.5 编写API集成测试

### 阶段四：前端会话管理 (P0)

- [x] 7.4.1 设计并实现左侧会话列表UI
- [x] 7.4.2 实现新对话功能
- [x] 7.4.3 实现会话切换功能
- [x] 7.4.4 实现会话列表加载和显示
- [x] 7.4.5 实现删除会话功能
- [x] 7.4.6 实现页面刷新恢复当前会话

### 阶段五：记忆增强功能 (P1)

- [ ] 7.5.1 实现会话自动标题生成（基于第一条消息）
- [ ] 7.5.2 实现重命名会话功能
- [ ] 7.5.3 实现记忆摘要生成
- [ ] 7.5.4 实现相关历史检索（增强上下文）

### 阶段六：优化和扩展 (P2)

- [ ] 7.6.1 实现消息搜索功能
- [ ] 7.6.2 实现会话列表分页加载
- [ ] 7.6.3 添加会话导出功能
- [ ] 7.6.4 可扩展向量存储接口（为语义检索做准备）

---

## 八、与现有系统集成

### 8.1 集成点分析

**现有流程**：
```
用户输入 → 前端收集 → 调用 /api/chat → LLM推理 → 返回结果
         ↑                                              ↓
         └────────── 历史消息在前端内存 ───────────────┘
```

**新流程（带记忆）**：
```
用户输入 → 前端收集 → 调用 /api/chat?session_id=xxx
         │
         ▼
    ┌─────────┐
    │ 后端检查 │
    │ session_id │
    └────┬────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  有ID      无ID
    │         │
    ▼         ▼
加载历史   创建新会话
    │         │
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ LLM推理 │◄── 上下文来自数据库
    └────┬────┘
         │
         ▼
    保存消息到数据库
         │
         ▼
    返回结果给前端
         │
         ▼
    前端更新UI
```

### 8.2 关键修改点

**app.py 修改**：
1. 初始化 `MemoryManager` 单例
2. 添加会话管理API端点
3. 修改 `/api/chat` 和 `/api/chat/stream` 支持 `session_id`
4. 消息发送后调用 `memory_manager.save_message()`

**chat.js 修改**：
1. 添加 `sessionId` 状态变量
2. 添加会话列表数据结构
3. 实现会话列表UI组件
4. 发送消息时携带 `session_id`
5. 切换会话时清空当前消息并加载历史

---

## 九、验收标准

### 9.1 功能验收

| 验收项 | 验收标准 | 状态 |
|--------|----------|------|
| 持久化存储 | 刷新页面后对话历史不丢失 | 待验证 |
| 会话创建 | 点击"新对话"创建新会话 | 待验证 |
| 会话切换 | 点击历史会话可恢复对话 | 待验证 |
| 会话删除 | 删除会话后不再显示 | 待验证 |
| 消息保存 | 每条消息都保存到数据库 | 待验证 |
| 上下文加载 | LLM能使用历史消息作为上下文 | 待验证 |

### 9.2 体验验收

| 验收项 | 验收标准 | 状态 |
|--------|----------|------|
| 会话列表 | 清晰显示历史对话，按时间排序 | 待验证 |
| 会话标题 | 标题有意义（基于对话内容） | 待验证 |
| 切换流畅 | 切换会话时无明显卡顿 | 待验证 |
| 操作反馈 | 删除、重命名等操作有明确反馈 | 待验证 |

### 9.3 代码验收

| 验收项 | 验收标准 | 状态 |
|--------|----------|------|
| 模块化 | 记忆模块独立，可单独测试 | 待验证 |
| 可扩展 | 存储层抽象，易于切换数据库 | 待验证 |
| 测试覆盖 | 核心功能有单元测试 | 待验证 |
| 文档完整 | 关键逻辑有注释 | 待验证 |

---

## 十、三轴评审检查清单

### 10.1 功能轴 (正确性)

#### 10.1.1 存储功能

- [x] SQLite 数据库正确初始化
- [x] 会话表、消息表、摘要表结构正确
- [x] 会话创建：生成唯一ID、时间戳正确
- [x] 消息保存：角色、内容、时间戳正确
- [x] 级联删除：删除会话时同时删除消息
- [ ] 并发安全：多线程环境下数据一致性

#### 10.1.2 会话管理

- [x] 创建会话：API返回正确的会话信息
- [x] 获取会话：返回指定会话的完整信息
- [x] 更新会话：标题修改正确保存
- [x] 删除会话：数据从数据库移除
- [x] 会话列表：按更新时间倒序排列
- [x] 空会话处理：无会话时返回空列表

#### 10.1.3 消息管理

- [x] 用户消息保存：role=user，内容正确
- [x] 助手消息保存：role=assistant，包含tool_calls
- [x] 工具消息保存：role=tool，包含tool_call_id
- [x] 消息加载：按创建时间正序排列
- [x] 截断处理：消息过多时合理截断上下文
- [x] 元数据保存：token使用、工具调用等信息正确存储

#### 10.1.4 API 接口

- [x] GET /api/sessions：返回正确格式
- [x] POST /api/sessions：创建成功
- [x] PUT /api/sessions/{id}：更新成功
- [x] DELETE /api/sessions/{id}：删除成功
- [x] GET /api/sessions/{id}：返回会话详情和消息
- [x] POST /api/chat 带 session_id：正确关联会话
- [x] POST /api/chat 无 session_id：自动创建新会话

#### 10.1.5 边界情况

- [ ] 空消息处理：不保存空内容
- [ ] 超长消息：正确处理大文本
- [x] 特殊字符：转义处理正确
- [x] 数据库异常：优雅降级，不影响聊天功能

### 10.2 体验轴 (可用性)

#### 10.2.1 会话列表UI

- [x] 布局合理：左侧边栏，不占用过多空间
- [x] 视觉清晰：会话标题、时间、状态区分明确
- [x] 滚动流畅：会话多时滚动不卡顿
- [x] 空状态：无会话时显示友好提示

#### 10.2.2 会话操作

- [x] 新对话：按钮明显，点击有反馈
- [x] 切换会话：点击有高亮，加载有状态提示
- [x] 删除会话：有确认弹窗，防止误操作
- [ ] 重命名会话：编辑模式直观，保存方便

#### 10.2.3 消息加载

- [x] 历史消息：切换会话时平滑加载
- [x] 加载状态：加载中显示loading
- [x] 空会话：新会话显示欢迎提示

#### 10.2.4 整体体验

- [x] 响应快速：操作无明显延迟
- [x] 状态一致：前端状态与后端同步
- [x] 错误提示：操作失败时有明确提示
- [x] 渐进增强：核心功能可用，高级功能可选

### 10.3 代码轴 (可维护性)

#### 10.3.1 架构设计

- [x] 分层清晰：UI → API → Manager → Store → DB
- [x] 职责单一：每个模块只负责一件事
- [x] 依赖方向：高层依赖低层抽象，不依赖具体实现
- [x] 可扩展性：存储层可替换，记忆检索可扩展

#### 10.3.2 代码质量

- [x] 命名规范：变量、函数、类命名有意义
- [x] 函数简洁：单个函数不超过50行
- [x] 类型注解：关键函数有类型提示
- [x] 异常处理：合理的try-catch，错误信息明确

#### 10.3.3 测试覆盖

- [ ] 单元测试：MemoryStore 核心操作
- [ ] 单元测试：MemoryManager 核心逻辑
- [ ] 集成测试：API 接口测试
- [ ] 边界测试：异常情况测试

#### 10.3.4 文档和注释

- [x] 模块文档：每个模块有功能说明
- [x] 函数文档：公共API有docstring
- [x] 复杂逻辑：关键算法有注释
- [x] 数据模型：表结构、字段含义说明

---

## 十一、测试验证计划

### 11.1 单元测试

**测试文件**：`tests/test_memory.py`

#### 11.1.1 MemoryStore 测试

```python
class TestMemoryStore:
    """记忆存储层测试"""
    
    def test_create_session(self):
        """测试创建会话"""
        # 创建会话
        # 验证ID、标题、时间戳
        pass
    
    def test_get_session(self):
        """测试获取会话"""
        # 创建会话后获取
        # 验证字段正确
        pass
    
    def test_update_session(self):
        """测试更新会话"""
        # 修改标题
        # 验证更新后的值
        pass
    
    def test_delete_session(self):
        """测试删除会话"""
        # 创建并删除
        # 验证删除后无法获取
        pass
    
    def test_list_sessions(self):
        """测试会话列表"""
        # 创建多个会话
        # 验证按时间倒序
        pass
    
    def test_add_message(self):
        """测试添加消息"""
        # 添加用户消息
        # 添加助手消息
        # 添加工具消息
        pass
    
    def test_get_messages(self):
        """测试获取消息"""
        # 添加多条消息
        # 验证顺序正确
        pass
    
    def test_cascade_delete(self):
        """测试级联删除"""
        # 会话有消息时删除会话
        # 验证消息也被删除
        pass
```

### 11.2 手动测试用例

#### TC-MEM-001：新对话创建

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证新对话能正确创建 |
| **前置条件** | 页面已加载 |
| **操作步骤** | 1. 点击"新对话"按钮<br>2. 观察左侧会话列表 |
| **预期结果** | 1. 会话列表新增"新对话"项<br>2. 新会话处于选中状态<br>3. 右侧消息区域清空 |

#### TC-MEM-002：消息持久化

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证消息正确保存到数据库 |
| **前置条件** | 有一个活跃会话 |
| **操作步骤** | 1. 发送问题："你好"<br>2. 等待回答<br>3. 刷新页面 |
| **预期结果** | 1. 刷新后会话列表仍有该会话<br>2. 点击会话显示历史消息<br>3. 用户消息和助手消息都存在 |

#### TC-MEM-003：会话切换

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证能正确切换不同会话 |
| **前置条件** | 已有两个会话：会话A、会话B |
| **操作步骤** | 1. 选中会话A<br>2. 查看显示的消息<br>3. 选中会话B<br>4. 查看显示的消息 |
| **预期结果** | 1. 切换A时显示A的消息<br>2. 切换B时显示B的消息<br>3. 切换过程无错误 |

#### TC-MEM-004：会话删除

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证会话能正确删除 |
| **前置条件** | 有一个可删除的会话 |
| **操作步骤** | 1. 点击会话的删除按钮<br>2. 在确认弹窗点击"确定" |
| **预期结果** | 1. 会话从列表消失<br>2. 自动切换到其他会话或新会话 |

#### TC-MEM-005：上下文延续

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证LLM能使用历史上下文 |
| **前置条件** | 有一个活跃会话 |
| **操作步骤** | 1. 发送："我叫小明"<br>2. 等待回答<br>3. 发送："我叫什么名字？" |
| **预期结果** | 1. 第二次回答应能说出"小明"<br>2. 说明上下文正确传递给LLM |

---

## 十二、项目文件结构

### 新增文件

```
agent_study/
├── agents/
│   └── memory/
│       ├── __init__.py          # 模块初始化
│       ├── models.py            # 数据模型类 (Session, Message, MemorySummary)
│       ├── store.py             # MemoryStore 存储层
│       └── manager.py           # MemoryManager 记忆管理器
├── mydocs/
│   └── memory_arch_plan.md      # 本文档
├── data/
│   └── agent_memory.db          # SQLite 数据库文件 (运行时创建)
└── tests/
    └── test_memory.py           # 记忆模块单元测试
```

### 修改文件

- `app.py` - 添加会话管理API，集成MemoryManager
- `static/js/chat.js` - 添加会话列表UI和交互逻辑
- `templates/index.html` - 添加左侧会话列表DOM结构

---

**文档状态**：✅ 规划完成
**指导文档**：`mydocs/memory_arch_plan.md`
**下一步**：按照阶段一到阶段六逐步实现代码
