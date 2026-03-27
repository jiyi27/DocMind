# API Key 管理 + OpenAI 兼容接口 + LLM 动态配置 设计方案

## 背景

本次目标拆成三件事，但实现上要彼此兼容：

1. LLM 配置改为数据库驱动，Admin 可在前端修改并立即生效
2. 用户可创建自己的 API Key，供外部客户端调用
3. 提供 OpenAI 兼容接口 `/v1/chat/completions`，支持第三方客户端直接接入

这版方案基于当前 DocMind 现状做了收敛，避免和现有 `chat` / `chat_stream` / LangGraph 调用链冲突。

---

## 一、总体原则

### 1. OpenAI 兼容接口完全无状态

`/v1/chat/completions` 不接入 DocMind 现有 session 系统：

- 不创建 `chat_sessions`
- 不写入 `chat_messages`
- 不生成会话标题
- 多轮上下文完全由客户端通过 `messages` 数组传入

它只是一个“OpenAI 风格的 RAG 推理入口”，不是 Web UI 对话系统的另一层包装。

### 2. Web Chat 与 OpenAI 兼容接口分两条链路

现有 Web Chat 仍保留当前行为：

- `/chat` 和 `/chat/stream` 继续使用 session + SQLite 消息持久化
- 前端 Web UI 体验不变

新增 OpenAI 兼容接口时，不去硬复用现有 session 持久化流程，而是只复用：

- 鉴权后的 `UserContext`
- retrieval 逻辑
- LLM 生成逻辑
- SSE 输出能力

### 3. LLM 配置以数据库为唯一运行时来源

LLM 聊天模型不再依赖进程启动时从 env 固化到 `settings.llm`：

- `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 不再是启动必填项
- 应用启动时不因缺失这些 env 而退出
- 运行时每次获取 LLM 时，都从数据库读取当前配置
- 若数据库未配置完整，调用处抛出明确业务异常，由前端展示错误

env 可以保留为“可选初始化来源”，但不是运行期的 source of truth。

### 4. OpenAI 兼容接口同时支持 stream 与非 stream

为了兼容更多第三方 SDK / 工具：

- `stream=true` 返回 OpenAI SSE
- `stream=false` 返回标准 JSON completion 响应

---

## 二、LLM 动态配置

### 数据存储

新增 `system_settings` 表，保存系统级配置：

```text
key                value
llm_base_url       https://openrouter.ai/api/v1
llm_api_key        sk-...
llm_model          anthropic/claude-3.5-sonnet
llm_max_messages   20
```

只放“运行时可热更新”的系统配置，不混入知识库级配置。

建议后续 repository 对外暴露聚合接口，而不是在业务层散读单个 key。

### 配置读取策略

新增 `SystemSettingsRepository`，负责：

- `get_llm_settings()`：读取当前 LLM 配置
- `upsert_llm_settings(...)`：更新 LLM 配置
- `is_llm_config_complete()`：判断配置是否完整

其中 `get_llm_settings()` 建议直接返回聚合结果，例如：

```python
{
    "base_url": "...",
    "api_key": "...",
    "model": "...",
    "max_messages": 20,
}
```

### LLM Factory 改造

当前项目里的 `get_llm()` 是基于 `settings.llm` 的进程单例，这里改成“数据库配置驱动的同步缓存工厂”：

- 缓存 key 使用 `(base_url, model, api_key)`
- 每次调用先读取当前 DB 配置
- 若命中缓存，返回已有 `ChatOpenAI`
- 若未命中，创建实例后写入缓存
- Admin 更新配置后，显式清空缓存

这里**不建议把 `get_llm()` 改成 async**，因为当前同步链路较多：

- `rag_graph.invoke(...)`
- retrieval graph 中的同步 node
- ingestion 中的代码摘要逻辑

如果直接改 async，会把同步调用链一并打断。

更稳妥的方式是：

- `get_llm()` 继续保持同步
- 底层通过同步 SQLite 读配置，或通过内存快照读配置
- 由 admin 更新操作主动刷新缓存

### 错误语义

若数据库中缺少 `base_url / api_key / model` 任一项：

- `get_llm()` 抛出 `ConfigError` 或专用 `LLMConfigError`
- API 层捕获后返回明确错误，例如 503 / 400
- 前端继续用 `ElMessage` 展示

这比启动直接失败更符合“配置运行时可修改”的目标。

### Admin API

新增 admin 设置接口，挂在 `require_super_admin` 下：

- `GET /admin/settings/llm`
- `PUT /admin/settings/llm`

行为约束：

- `GET` 返回脱敏后的 `api_key`
- `GET` 同时返回 `max_messages`
- `PUT` 更新成功后清空 LLM 缓存，后续请求立即生效
- `PUT` 支持同时更新 `base_url / api_key / model / max_messages`
- 不在 API handler 里写配置拼装逻辑，真正的数据读写放 repository / service

`max_messages` 的定位是“系统统一聊天历史上限”，由超管配置一次后，全站共用：

- Web Chat 裁剪数据库会话历史时使用它
- OpenAI 兼容接口裁剪客户端传入 `messages` 时也使用它

这样可以避免再保留额外 env 或单独的 OpenAI compat 配置项。

---

## 三、API Key 管理

### 数据模型

```text
api_keys
  id
  user_id
  key_hash
  key_prefix
  name
  daily_limit
  is_active
  created_at
  last_used_at

api_key_usage
  key_id
  used_date
  count
  PRIMARY KEY (key_id, used_date)
```

设计说明：

- 原始 key 只在创建时返回一次
- 数据库只存 hash，不存明文
- `key_prefix` 仅用于展示与运维定位
- `daily_limit` 为每个 key 独立限额
- `used_date` 使用 UTC 日期

### Key 格式

建议：

- 前缀：`dm_`
- 主体：高熵随机串

例如：

```text
dm_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 生成与验证

新增 `docmind/auth/api_key.py`：

```python
def generate_api_key() -> tuple[str, str, str]:
    # 返回 (raw_key, key_hash, key_prefix)

def hash_api_key(raw_key: str) -> str:
    # sha256(raw_key)
```

### 使用计数与限流

每次 API Key 请求时：

1. 校验 key 是否存在且启用
2. 原子递增当日用量
3. 检查是否超过 `daily_limit`
4. 超限返回 429

SQL 可以继续采用：

```sql
INSERT INTO api_key_usage (key_id, used_date, count)
VALUES (?, ?, 1)
ON CONFLICT(key_id, used_date)
DO UPDATE SET count = count + 1;
```

之后读取当日计数判断是否超限。

注意：

- 严格来说这是“先记账后判定”
- 如果超限仍记入一次，可接受，逻辑更简单
- 如果要做到“超过就完全不计入”，需要更复杂的事务控制

当前阶段建议先采用“先记账后判定”。

### API 路由

新增 `/api-keys`，使用 JWT 鉴权：

| 方法     | 路径             | 说明                               |
| -------- | ---------------- | ---------------------------------- |
| `POST`   | `/api-keys`      | 创建 key，返回原始 key（仅此一次） |
| `GET`    | `/api-keys`      | 列出当前用户所有 key               |
| `DELETE` | `/api-keys/{id}` | 吊销 key，设 `is_active=0`         |

可以考虑补一个更新限额接口，但不是首期必须。

---

## 四、OpenAI 兼容接口

### 路由

新增：

- `POST /v1/chat/completions`

使用新的 `get_user_from_api_key` 依赖。

### 鉴权 Dependency

`get_user_from_api_key` 放在 `docmind/api/dependencies.py`：

1. 从 `Authorization: Bearer <key>` 读取原始 key
2. 对 key 做 hash
3. 查询 `api_keys`，并 join `users` + `knowledge_bases`
4. 校验 `is_active`
5. 递增并检查当日额度
6. 返回 `UserContext`

这里返回的 `UserContext` 结构与 JWT 依赖保持一致，便于复用 retrieval / generation 逻辑。

### 请求模型

建议支持 OpenAI 常见字段，但只消费必要子集：

```python
class OAIMessage(BaseModel):
    role: str
    content: str


class OAIChatRequest(BaseModel):
    model: str | None = None
    messages: list[OAIMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
```

说明：

- `model` 先忽略，不允许客户端覆盖服务端 KB/LLM 绑定关系
- `temperature` 等先忽略，但请求模型层面允许存在，避免第三方 SDK 因额外字段报错
- 必须校验 `messages` 非空

### 上下文处理

OpenAI 兼容接口不落库，但**必须消费客户端传来的历史消息**。

推荐逻辑：

1. 找出最后一条 `role=user` 的消息，作为当前 query
2. 取它之前的若干条消息，映射成 LangChain `HumanMessage` / `AIMessage`
3. 按系统设置中的 `max_messages` 对历史条数做上限裁剪
4. 将裁剪后的 history 传给生成逻辑

这样可兼顾两点：

- 保持 OpenAI 风格的无状态调用
- 不丢失客户端自行维护的上下文

### 历史消息限制

不再新增 env，也不再给 OpenAI compat 单独加一套配置。

统一规则：

- 系统设置中新增 `max_messages`
- Web Chat 与 OpenAI compat 都遵守这个上限
- 只保留最近 N 条历史消息参与生成

两条链路的裁剪对象不同，但上限值相同：

- Web Chat：裁剪从 SQLite 读出的会话历史
- OpenAI compat：裁剪客户端传入的 `messages` 历史

建议实现时明确一个统一细节：

- 最后一条当前 `user` 消息是否计入 `max_messages`

推荐做法：

- `max_messages` 只约束“历史消息”
- 当前最后一条 user query 不计入上限

这样实现和理解都更直观。

### 非流式响应

当 `stream=false` 时，返回标准 OpenAI JSON：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "docmind",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

实现建议：

- 走一次 retrieval
- 调用非流式生成逻辑
- 返回拼装后的 OpenAI JSON

### 流式响应

当 `stream=true` 时，返回标准 OpenAI SSE：

```text
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,
       "model":"docmind","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,
       "model":"docmind","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,
       "model":"docmind","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

第一帧继续发送：

```json
{"role":"assistant","content":""}
```

兼容部分依赖初始化 delta 的客户端。

### 与现有 `chat_stream` 的关系

现有 `/chat/stream` 输出的是 DocMind 自定义 SSE：

- `type: sources`
- `type: chunk`
- `type: done`

OpenAI 兼容接口不能直接复用这个 SSE 输出格式，必须做一层适配。

建议复用：

- retrieval 逻辑
- `stream_generate(...)`

但新增独立的 OpenAI SSE 包装器，不污染现有 Web UI 协议。

### sources 的处理

OpenAI 协议本身没有 DocMind 现有的独立 `sources` 事件。

首期建议：

- 不单独透出 sources 事件
- 只在模型回答文本中体现引用信息

如果未来需要，可考虑：

- 放进额外字段
- 或放进兼容接口的扩展响应头 / 尾块

但首期不建议破坏 OpenAI 客户端兼容性。

---

## 五、现有 Chat 接口的适配

由于 LLM 配置改为数据库驱动，现有 `/chat` 与 `/chat/stream` 也需要一起适配错误处理。

目标是：

- 若 LLM 未配置，Web Chat 不崩
- 后端返回明确错误
- 前端通过现有全局错误处理和 `ElMessage` 提示用户

建议：

1. 在 `get_llm()` 处抛出明确配置异常
2. 在 API 层统一转换成可展示的 HTTP 错误
3. 不把原始 Python traceback 暴露给前端

这符合当前项目的错误边界约束。

---

## 六、建议的模块拆分

### 数据层

- `docmind/db/models.py`
  新增 `system_settings`、`api_keys`、`api_key_usage`

- `docmind/db/repositories.py`
  新增：
  - `SystemSettingsRepository`
  - `ApiKeyRepository`

### 认证层

- `docmind/auth/api_key.py`
  API Key 生成与 hash 工具

- `docmind/api/dependencies.py`
  新增 `get_user_from_api_key`

### LLM 层

- `docmind/core/llm.py`
  改造为数据库配置驱动的同步缓存工厂

可以考虑额外抽一个：

- `docmind/services/system_settings.py`
  处理 LLM 配置聚合、缓存清理等逻辑

这样 API handler 会更薄。

### API 层

- `docmind/api/routers/api_keys.py`
  API Key CRUD

- `docmind/api/routers/openai_compat.py`
  `/v1/chat/completions`

- `docmind/api/routers/admin.py`
  LLM 设置 GET/PUT

- `docmind/api/main.py`
  注册新路由

---

## 七、实现顺序建议

### Phase 1: 数据与配置基础设施

1. 增加 `system_settings` / `api_keys` / `api_key_usage` 表
2. 增加 repository
3. 重构 `get_llm()` 为数据库配置驱动
4. 调整启动校验，去掉 LLM env 强依赖
5. 验证现有 `/chat` 与 `/chat/stream` 在“未配置 LLM”时能正确报错

### Phase 2: Admin LLM 设置

1. 增加 `GET /admin/settings/llm`
2. 增加 `PUT /admin/settings/llm`
3. 在该设置中加入 `max_messages`
4. 增加前端设置页或管理入口
5. 更新成功后清理 LLM 缓存

### Phase 3: API Key 管理

1. 增加 API Key 生成 / 列表 / 吊销接口
2. 增加使用量统计与每日限额
3. 前端增加 API Key 管理界面

### Phase 4: OpenAI 兼容接口

1. 增加 `get_user_from_api_key`
2. 增加 `POST /v1/chat/completions`
3. 实现非流式 JSON 响应
4. 实现流式 SSE 响应
5. 接入系统级 `max_messages` 裁剪逻辑
6. 做第三方客户端联调

---

## 八、最终定稿要点

这版方案的关键调整是：

- OpenAI 兼容接口无状态，不保存聊天记录
- 兼容接口消费客户端传来的 `messages` 历史，而不是只取最后一句就丢掉前文
- LLM 配置从 env 启动时单例，改为数据库驱动的运行时配置
- 聊天历史上限也纳入数据库系统设置，由超管统一配置
- 不把 `get_llm()` 改成 async，避免打断当前同步调用链
- 同时支持 `stream` 和非 `stream`

这几条和当前项目结构更一致，实施风险也更低。
