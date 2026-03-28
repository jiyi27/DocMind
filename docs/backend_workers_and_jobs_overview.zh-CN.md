`ConfluenceSyncWorker` 负责知识库级别的 Confluence 同步, 它会定时扫描开启自动同步的知识库, 用户也可以在 KB 详情页点击 `Sync Now` 手动触发, 无论是哪种方式, worker 都会先创建一条 `kb_sync_job`, 表示"一次完整的知识库同步任务"开始了, 这条任务不只是给前端展示状态, 也承载这次同步过程本身

在执行这条 `kb_sync_job` 时, `ConfluenceSyncWorker` 会真正去遍历该知识库配置的 Confluence 页面树, 并与本地已有的 Confluence 文档做对比, 判断每个页面是新增, 更新还是删除, 对于新增和更新的页面, 它会拉取最新内容, 保存本地文件, 更新或重建 `documents` 记录, 并创建对应的 `ingestion_jobs`, 这些 `ingestion_jobs` 后续会交给 `IngestionQueueWorker` 做切块, 向量化和写入 Qdrant, 对于删除的页面, 它会清理对应的本地数据和向量数据

最后, `ConfluenceSyncWorker` 会把每个页面的处理结果写入 `kb_sync_records`, 并回写 `kb_sync_job` 和 `knowledge_bases` 的同步状态, 可以把它理解成: `kb_sync_job` 是一次知识库级别的"同步任务", 而 `ingestion_job` 是一次文档级别的"入库任务"

也就是说 `IngestionQueueWorker` 才是真正负责干活切片入库的人, 它会持续扫描 ingestion_jobs，把待处理文档做完整的 ingest 流程：读文件、切 chunk、生成 embedding、写入 Qdrant，然后更新任务和文档状态。ingestion_jobs 的来源有两种：一种是用户手动上传文档时创建，另一种是 Confluence 同步过程中发现页面需要新增或更新时创建

```text
后端后台逻辑
├─ 常驻 worker 一共有 2 个
│
├─ 1. ConfluenceSyncWorker
│ ├─ 主要读取的主表
│ │ └─ knowledge_bases
│ ├─ 主要写入的表
│ │ ├─ kb_sync_jobs
│ │ ├─ kb_sync_records
│ │ └─ knowledge_bases
│ ├─ 它处理的 job
│ │ └─ kb_sync_jobs
│ │ └─ 表示"某个 KB 要执行一次 Confluence 同步"
│ ├─ job 的来源
│ │ ├─ 自动定时扫描后创建
│ │ └─ 手动触发 Confluence 同步时创建, 在 Kb Detail 点击 Sync Now 触发
│ └─ 主要流程
│ ├─ 扫描 knowledge_bases
│ ├─ 找出开启自动同步且到时间的 KB
│ ├─ 为该 KB 创建一条 kb_sync_job
│ ├─ 遍历该 KB 配置的 Confluence 页面树
│ ├─ 对比本地已有 Confluence 文档
│ ├─ 得到三类页面动作
│ │ ├─ create
│ │ │ ├─ 拉取页面内容并保存为本地文件
│ │ │ ├─ 创建 documents 记录
│ │ │ ├─ 创建 ingestion_jobs
│ │ │ └─ 写一条 kb_sync_record
│ │ ├─ update
│ │ │ ├─ 拉取最新页面内容并保存为本地文件
│ │ │ ├─ 删除旧 documents 对应的本地数据和向量
│ │ │ ├─ 重建 documents 记录
│ │ │ ├─ 重建 ingestion_jobs
│ │ │ └─ 写一条 kb_sync_record
│ │ └─ delete
│ │ ├─ 删除 documents 对应的本地数据和向量
│ │ └─ 写一条 kb_sync_record
│ └─ 回写 kb_sync_job 和 knowledge_bases 的同步状态
│
├─ 2. IngestionQueueWorker (实际操作每个文档进行 ingest 的工人)
│ ├─ 主要读取的主表
│ │ └─ ingestion_jobs
│ ├─ 主要写入的表
│ │ ├─ ingestion_jobs
│ │ ├─ documents
│ │ └─ Qdrant
│ ├─ 它处理的 job
│ │ └─ ingestion_jobs
│ │ └─ 表示"某个 document 要执行入库/切块/向量化"
│ ├─ job 的来源
│ │ ├─ 手动上传文档时创建
│ │ └─ Confluence 同步过程中发现页面需要新增或更新时创建
│ └─ 主要流程
│ ├─ 定时扫描 ingestion_jobs
│ ├─ 取出一条 pending job
│ ├─ 执行一整套 ingest 流程
│ │ ├─ 读文件
│ │ ├─ 切 chunk
│ │ ├─ embedding
│ │ └─ 写入 Qdrant
│ └─ 回写 ingestion_jobs 和 documents 的状态
│
└─ ingestion_jobs
   ├─ 是什么
   │ └─ 一条 document 级别的入库任务
   ├─ 由谁处理
   │ └─ IngestionQueueWorker
   └─ 来源
      ├─ 手动上传文档时会创建一个 ngestion_job
      └─ Confluence 同步 scan 中的 create / update
```
