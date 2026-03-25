## 1. 前置: `yield` 的本质与使用时机

在深入细节之前, 先建立两个最核心的认知

### 1.1. `yield` 的本质: 协作式控制权转让

`yield` 的本质是**把执行权暂时交还给调用方, 同时保留自己的完整状态 (局部变量, 执行位置)**, 等待下次被唤醒时从断点继续

这与普通函数的 `return` 有根本区别

| | `return` | `yield` |
| -------------- | ------------------ | --------------------- |
| 执行后函数状态 | **销毁**, 栈帧释放 | **冻结**, 栈帧保留 |
| 能否继续执行 | 不能 | 能, 从断点恢复 |
| 调用方拿到值后 | 函数已消失 | 函数还在等待 |
| 适合场景 | 一次性计算 | 需要"暂停-恢复"的流程 |

> **一句话**: `return` 是"我做完了, 给你结果, 再见", `yield` 是"我先把东西给你, 我在这等着, 你用完告诉我"

### 1.2. 什么情况下用 `yield` 才有意义

> 用 `yield` 的唯一理由是——你现在不想 (或不能) 一次性给出全部结果, 你需要"分批"或"适时"地交付数据, 同时保持工作状态等待下一次交付

#### 场景一: 大数据流 —— 内存不够时的救星

```python
# ❌ 用 return: 一次性加载 10GB 到内存, 电脑卡死
def read_logs():
    with open("huge.log") as f:
        return f.readlines()

# ✅ 用 yield: 每次只读一行, 内存占用 < 1MB
def read_logs():
    with open("huge.log") as f:
        for line in f:
            yield line

for line in read_logs():
    process(line)
```

**决策点**: 数据量超过内存容量, 或数据是实时产生的 (网络流, 传感器), 必须用 `yield`

#### 场景二: 无限序列 —— `return` 无法实现

```python
# 斐波那契数列是无限的, 无法 return 一个"完整的列表"
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

fib = fibonacci()
for _ in range(100):
    print(next(fib)) # 取前 100 个, 随时可停
```

**决策点**: 序列无限, 长度未知, 或持续实时产生 (股票行情, 聊天消息)

> 这里生成器是一个"活着的" 可以被多次唤醒的函数对象, 也就是说我们的循环执行一百次后 fibonacci() 函数没有被销毁 一直暂停在那里 可以被其他人调用 且维持内部状态
> 如何"杀死"这个生成器? 手动关闭: fib.close()

#### 场景三: 状态保持 —— 函数需要"记住"上次到哪了

```python
# 令牌桶限流器: 函数需要在多次调用间记住剩余令牌数
import time

def token_bucket(rate, capacity):
    tokens = capacity
    last_time = time.time()
    while True:
        now = time.time()
        tokens = min(capacity, tokens + (now - last_time) * rate)
        last_time = now
        tokens -= 1
        yield tokens >= 0 # 允许或拒绝

limiter = token_bucket(rate=10, capacity=10)
for request in requests:
    if next(limiter): # 函数记得上次剩多少令牌
        handle(request)
    else:
        reject(request)
```

**决策点**: 函数需要维护内部状态, 且要在多次调用间保持, 用 `yield` 比用 `class` 更简洁

#### 场景四: 上下文管理 —— 资源的自动进入/退出

```python
@contextmanager
def managed_resource():
    resource = acquire()
    try:
        yield resource # 必须是 yield, 因为要等待 with 块执行完毕
    finally:
        release(resource) # 保证执行, 即使 with 块内抛出异常
```

**决策点**: 需要在代码块前后自动执行操作 (进入/退出), 且要把资源交给调用方临时使用, 这也是本文的核心场景

#### 快速决策流程

```
开始
 │
 ▼
数据是流式的/无限的/巨大? ──Yes──► 使用 yield(生成器)
 │ No
 ▼
需要暂停等待异步事件? ──Yes──► 使用 async yield
 │ No
 ▼
需要保存函数内部状态 (如协程)? ──Yes──► 使用 yield
 │ No
 ▼
需要资源自动进入/退出管理? ──Yes──► 使用 @contextmanager + yield
 │ No
 ▼
数据量小且需要反复使用? ──Yes──► 使用 return 列表
```

## 2. 生成器基础 —— `yield` 与 `next()`

### `next()` 是生成器的点火钥匙

生成器创建后处于**冻结状态**, 必须用 `next()` 来推动它

```python
gen = generator()

value1 = next(gen) # 执行到第一个 yield, 暂停, 返回 42
# 输出: 步骤 1
# value1 == 42

value2 = next(gen) # 从上次暂停处继续, 执行到第二个 yield
# 输出: 步骤 2
# value2 == 100

next(gen) # 没有更多 yield, 抛出 StopIteration
```

**核心规律**: 生成器不会自己跑, 每次 `next()` 让它向前走一步, 走到下一个 `yield` 就再次冻结

### 谁在实际调用 `next()`

日常业务代码中**通常不需要手动写 `next()`**, 因为

| 场景 | 谁调用 `next()` |
| ------------------------------- | ---------------------------- |
| `for x in gen:` | `for` 循环底层自动调用 |
| `list(gen)` | `list()` 自动调用 |
| `with` 语句 + `@contextmanager` | 装饰器内部自动调用 |
| FastAPI `Depends()` | FastAPI 依赖注入系统自动调用 |

## 3. `yield` 实现"进入-退出"逻辑

`yield` 的暂停特性天然适合做资源管理: **yield 前是准备工作, yield 后是清理工作, 中间是资源使用时间**

```
yield 前 (准备) → yield(交出资源) → yield 后 (清理)
     ↑ ↑ ↑
  获取连接/锁 用户使用资源 关闭连接/释放锁
```

> 问题: 如果中途抛出异常怎么办? 
>
> 如果手动管理 `next()`, 一旦中间出错, 清理代码可能永远不会执行, 这就是 `@contextmanager` 存在的原因

## 4. `@contextmanager` 是自动化的 `next()` 调用器

`@contextmanager` 把生成器包装成一个标准的上下文管理器 (拥有 `__enter__` 和 `__exit__`), 自动处理 `next()` 调用和异常安全

```python
from contextlib import contextmanager

@contextmanager
def my_resource():
    print("获取资源")
    yield "资源句柄"
    print("释放资源")

with my_resource() as res:
    print(f"使用 {res}")
```

**`with` 语句内部等价于**

```python
gen = my_resource()

# 1. 自动调用 next(), 执行到 yield, 拿到资源
res = next(gen) # 输出"获取资源"

# 2. 执行 with 块内的代码
print(f"使用 {res}")

# 3. with 块结束 (无论是否异常), 自动调用 next() 执行清理
try:
    next(gen) # 输出"释放资源"
except StopIteration:
    pass # 正常结束
```

**异常安全**: 如果 `with` 块内抛出异常, 装饰器会捕获它, 仍然执行 `yield` 后的清理代码, 然后再重新抛出异常


## 5. 异步版本 `@asynccontextmanager`

数据库连接, 网络请求等 I/O 操作需要异步处理, 异步世界里, 推动生成器的不是 `next()`, 而是 `await __anext__()`

`@asynccontextmanager` 是 `@contextmanager` 的异步版本, 原理完全相同

## 6. DocMind 项目中的真实案例

### 案例 1: `get_db()` —— 全局单例连接的借用

```python
# backend/docmind/db/database.py

_GLOBAL_CONN: aiosqlite.Connection | None = None

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields the global database connection."""
    if _GLOBAL_CONN is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    # Yield the global connection without closing it
    yield _GLOBAL_CONN
    # yield 后没有代码 —— 因为连接是全局单例, 不能在这里关闭
```

**为什么 `yield` 后面没有代码? **

`_GLOBAL_CONN` 是应用级别的**全局单例**, 在应用启动时创建, 关闭应用时才销毁, `get_db()` 只是把它**临时借给**当前请求使用

- **yield 前**: 检查连接是否已初始化 (进入阶段)
- **yield 时**: 把连接交出去给路由函数使用
- **yield 后**: 什么都不做 (连接不能关, 还要留给下一个请求)

对比: 如果是**每次请求新建连接**的模式, 代码应该是

```python
@asynccontextmanager
async def get_db():
    conn = await aiosqlite.connect("data/docmind.db") # 每个请求新建连接
    yield conn
    await conn.close() # 请求结束后关闭 (清理)
```

### 案例 2: `lifespan()` —— 应用生命周期管理

```python
# backend/docmind/api/lifespan.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks and initialize resources before accepting requests."""
    # --- yield 前: 应用启动阶段 ---
    missing = settings.validate()
    if missing:
        # 缺少环境变量, 直接退出
        sys.exit(1)

    await init_db() # 初始化数据库, 创建全局连接 _GLOBAL_CONN

    yield # App is running(FastAPI 在这里接受请求)

    # --- yield 后: 应用关闭阶段 ---
    await close_db() # 关闭全局连接, 释放资源
```

这里的 `yield` 后面**有**清理代码, 因为 `lifespan` 管理的是整个应用的生命周期

```
应用启动
   ↓
validate settings
   ↓
init_db() ←── 创建 _GLOBAL_CONN
   ↓
yield ←── FastAPI 开始接受请求 (可能持续数小时)
   ↓
(收到关闭信号)
   ↓
close_db() ←── 销毁 _GLOBAL_CONN
   ↓
应用退出
```

### 案例 3: 路由中使用 `get_db()`

```python
# backend/docmind/api/routers/auth.py

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate):
    async with get_db() as db:
        kb_repo = KBRepository(db)
        user_repo = UserRepository(db)

        kb = await kb_repo.get_by_id(body.kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # ... 业务逻辑 ...
```

**执行时序**

```
POST /auth/register 请求进入
   ↓
async with get_db() as db:
   ↓
装饰器内部 await __anext__()
   ↓
检查 _GLOBAL_CONN 是否存在
   ↓
yield _GLOBAL_CONN → db 变量拿到连接
   ↓
执行路由业务逻辑 (查询 KB, 创建用户...)
   ↓
with 块结束 (正常或异常)
   ↓
装饰器再次 await __anext__()
   ↓
yield 后无代码, 生成器结束 (StopIteration)
   ↓
请求处理完毕
```

### 总结: 三个层次的 `yield`

| 层次 | 代码位置 | yield 前 | yield 后 |
| -------------- | ------------------------ | -------------------------- | ----------------- |
| 应用生命周期 | `lifespan.py` | 初始化 DB, 校验配置 | 关闭 DB 连接 |
| 请求级连接借用 | `database.py` `get_db()` | 检查连接存在 | 无 (单例不关闭) |
| 路由业务逻辑 | `routers/*.py` | `async with get_db()` 开始 | `async with` 结束 |
