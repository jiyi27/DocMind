## 1. 为什么不继续使用原来的 BackgroundTasks

`BackgroundTasks` 适合短小, 轻量, 对时延不敏感的后台收尾动作, 例如

- 记录审计日志
- 发送一个简单通知
- 做一次快速缓存刷新

它不适合承担 DocMind 当前这种"完整文档入库工作流"的原因是

- 入库流程耗时长
- 涉及多步同步处理
- 失败后需要持久化状态
- 服务重启后不能丢任务
- 需要可恢复, 可观察, 可串行控制

换句话说, `BackgroundTasks` 更像"请求结束后的顺手做点事", 而不是"一个正式的, 可恢复的任务系统"

## 2. 为什么没有直接上 Redis / Celery / ARQ

从工程成熟度看, 外部队列系统当然更标准, 但结合当前项目阶段, 我们没有直接引入 Redis 或专门的异步任务框架, 主要基于下面几个判断

### 2.1 当前目标是先解决核心问题

我们这次优先要解决的是

- 上传接口不要被入库流程拖住
- 队列状态要持久化
- 服务重启后任务不要丢
- 同一时刻只处理一个文档, 降低系统压力

这些目标并不一定要求引入外部基础设施

### 2.2 当前项目更适合轻量方案

DocMind 目前的后端本身已经依赖 SQLite, 并且使用单机开发/运行模式, 
在这个前提下, 先做一个"数据库持久化队列 + 单消费者 worker"有几个优势

- 实现成本低
- 部署方式变化小
- 不需要新增 Redis 容器或服务
- 对现有代码侵入有限
- 能明显降低复杂度

### 2.3 当前并不追求高吞吐并发消费

当前目标不是"同时处理很多文档", 而是"稳定, 可恢复, 顺序处理", 
因此我们选择了单消费者 worker, 而不是多 worker 并行消费

## 3. 最终采用的方案

最终采用的是

**数据库持久化队列 + 单消费者 worker 线程**

核心思路如下

1. 上传接口只负责接收文件, 写数据库, 返回响应
2. 真正的 LangGraph 入库工作由独立 worker 在后台串行执行
3. 队列状态保存在 SQLite 中, 而不是内存中
4. 应用重启后, worker 会重新扫描未完成任务并继续处理

这套方案兼顾了

- 简单
- 可持久化
- 可恢复
- 串行处理
- 对现有系统改动可控

## 4. 当前架构设计

### 角色划分

当前设计中有三个关键角色

- HTTP 上传接口
- SQLite 持久化任务表
- 单消费者 ingestion worker

它们的职责边界如下

#### HTTP 上传接口

位于 `backend/docmind/api/routers/ingest.py`

职责

- 校验请求
- 保存上传文件到临时目录
- 创建 `documents` 记录
- 创建 `ingestion_jobs` 记录
- 立即返回响应

它**不再负责**执行 LangGraph 工作流

#### `documents` 表

它代表"业务实体", 也就是用户上传的文档本身, 
前端展示文档列表时, 读取的仍然是 `documents` 表中的状态

典型字段包括

- `id`
- `user_id`
- `kb_id`
- `file_name`
- `title`
- `doc_type`
- `chunk_count`
- `status`
- `error_message`
- `file_path`
- `strict_mode`

#### `ingestion_jobs` 表

它代表"执行实体", 也就是某个文档的一次入库任务

当前字段包括

- `id`
- `document_id`
- `payload_json`
- `status`
- `attempt_count`
- `error_message`
- `claimed_at`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

这里有一个关键设计点: `payload_json`

### 为什么新增了 `payload_json`

一开始看起来似乎只保存 `document_id` 就够了, 但实际并不够

原因是 LangGraph 入库执行所需的输入, 不只来自 `documents` 表, 还包括

- `metadata.url`
- `metadata.service`
- `metadata.department`
- `chunk_size`
- `max_chunk_size`
- `kb_name`

这些数据如果只存在于请求上下文里, 那么一旦服务重启, worker 就无法恢复任务

因此我们把 LangGraph 所需的完整执行入参序列化进 `payload_json`, 这样任务就具备了真正的"可恢复执行"能力

这也是数据库持久化队列里最重要的一个实现细节

## 5. Worker 的运行方式

worker 位于 `backend/docmind/ingestion/worker.py`, 并在 `backend/docmind/api/lifespan.py` 中启动

应用启动时

1. 先初始化数据库
2. 再启动 `IngestionQueueWorker`
3. worker 在后台线程中循环扫描 `ingestion_jobs`

应用关闭时

1. 设置停止信号
2. 等待 worker 线程退出
3. 再关闭全局数据库连接

这样可以保证 worker 生命周期和应用本身一致

## 6. 为什么 worker 线程不用现有的 aiosqlite 全局连接

这是一个很重要的实现决策

当前项目在 `backend/docmind/db/database.py` 中维护了一条全局 `aiosqlite` 连接, 并通过 `get_db()` 暴露给请求使用

这条连接适合请求协程使用, 但不适合直接跨线程给 worker 复用, 原因包括

- worker 是单独的后台线程
- `aiosqlite` 的使用语义本质上仍围绕事件循环
- 跨线程共享同一条异步连接会让边界变得不清晰, 也更容易埋并发问题

因此当前实现选择

- Web 请求继续使用现有 `aiosqlite` 全局连接
- worker 自己单独创建同步 `sqlite3.connect(...)` 连接

这能让两类访问边界更清晰

- 请求侧: 异步, 短事务
- worker 侧: 同步, 串行, 长时任务驱动

## 8. 当前任务处理流程

### 8.1 上传阶段

上传请求到来后

1. 校验 KB 是否存在
2. 生成 `doc_id`
3. 将文件写入 `data/uploads`
4. 创建 `documents` 记录, 初始状态为 `pending`
5. 创建 `ingestion_jobs` 记录, 状态也为 `pending`
6. 立即返回上传成功响应

此时, 前端已经能通过文档列表接口看到这条文档

### 8.2 消费阶段

worker 会按 `created_at ASC` 顺序扫描 `pending` 任务, 并执行

1. 找到最早的 `pending` job
2. 将 job 置为 `processing`
3. 将对应 `documents.status` 置为 `processing`
4. 从 `payload_json` 反序列化 LangGraph 入参
5. 执行 `ingestion_graph.invoke(...)`
6. 成功时更新
   - `documents.status = completed`
   - `documents.chunk_count`
   - `ingestion_jobs.status = completed`
7. 失败时更新
   - `documents.status = failed`
   - `documents.error_message`
   - `ingestion_jobs.status = failed`
   - `ingestion_jobs.error_message`
8. 最后删除临时上传文件

### 8.3 启动恢复阶段

如果服务异常重启, 可能会留下状态为 `processing` 的任务, 
当前 v1 的恢复策略比较直接

- 应用启动时, 把所有 `processing` job 重置为 `pending`
- 对应 `documents.status` 也重置为 `pending`

这样 worker 会重新消费它们

这是一种偏保守但非常实用的恢复策略, 适合当前单 worker 架构

## 9. 为什么当前仍然保留"认领任务"这一步

虽然当前系统设计上只有一个 worker, 但代码里仍然保留了"认领任务"的模式, 也就是

1. 先查询一条 `pending`
2. 再按 `id + status='pending'` 更新为 `processing`
3. 如果更新不到, 说明该任务已被别人先处理

当前单 worker 场景下, 这一步看起来有点多余, 但它的价值在于

- 让状态流转更清晰
- 为以后误启动多个 worker 留出最低限度保护
- 避免将来扩展时重写整套消费逻辑

所以这是一种"现在成本不高, 但未来有价值"的设计

## 10. 前端为什么只做静默刷新, 不做更复杂的 optimistic UI

当前前端的核心问题不是没有轮询, 而是上传后刷新列表时会触发全量 loading, 
因此这次前端只做了一个非常克制的改动

- 初次进入页面: 允许显示 skeleton
- 上传后刷新: 改为静默刷新
- 轮询刷新: 继续静默刷新

这样做的原因是

- 改动小
- 风险低
- 能直接解决"列表消失"的体验问题
- 不需要修改现有接口返回结构

我们没有在这次实现中加入"上传成功后立即把文档插进列表顶部"的 optimistic UI, 原因是当前上传接口返回字段还不足以稳定渲染完整列表项, 
先把数据链路和状态链路跑通, 比先做体验花活更重要

## 11. 这套方案的主要优点

### 11.1 优点

- 上传接口立即返回, 用户响应更快
- 入库任务持久化, 重启后不丢
- 串行处理降低并发压力
- 状态链路更清晰, 前端能稳定轮询中间态
- 不需要引入 Redis, Celery, ARQ
- 和当前项目的单机 SQLite 架构比较匹配

### 11.2 当前限制

这套方案不是没有边界, 当前限制主要包括

- 假设部署为单进程, 单实例
- 只有一个 worker, 吞吐量有限
- 不支持真正的分布式消费
- 没有实现任务重试上限
- 没有实现任务历史版本
- 没有做管理后台级别的任务监控界面

所以它是一个"当前阶段非常合适"的方案, 而不是"最终形态"

## 12. 后续可演进方向

如果未来文档量, 并发量或部署复杂度上升, 可以按下面顺序继续演进

### 12.1 继续完善当前 SQLite 队列

可以追加

- 重试次数上限
- 手动重试入口
- 卡死任务超时判定
- 更细粒度的任务日志

### 12.2 将 worker 从应用进程中拆出

即使仍然用 SQLite, 也可以把 worker 做成单独进程, 进一步减少 API 进程与消费进程耦合

### 12.3 升级到外部队列系统

当出现这些需求时, 再考虑 Redis / Celery / ARQ 会更合理

- 多实例部署
- 多 worker 并发消费
- 更强的重试与调度能力
- 更完整的任务监控体系
