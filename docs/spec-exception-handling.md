# 规范：异常处理与全局 Handler（Exception Handling）

> 本文档描述一套适用于 FastAPI 服务的异常分层处理机制。
> AI Agent 在实现新项目时，应严格参照本规范构建异常层。
> 具体的异常类型（如哪些业务领域需要哪些异常子类）由 Agent 根据实际项目自行设计。

---

## 一、核心原则

1. **业务层只负责 raise，不负责翻译**：核心代码抛出语义明确的自定义异常，不关心 HTTP。
2. **API 层负责翻译**：全局 handler 统一将所有异常转化为统一响应信封。
3. **用户安全性边界**：内部 traceback、堆栈信息、原始异常消息绝不暴露给客户端。
4. **日志完整性**：对用户隐藏的信息必须在服务端完整记录，包括 traceback。

---

## 二、自定义异常层级

### 2.1 基类设计

在 `your_app/core/exceptions.py` 中定义一个项目级基类：

```python
class AppException(Exception):
    """所有业务异常的基类。

    message 字段是面向用户安全的文案，可以直接暴露给客户端。
    当调用方不传 message 时，使用 default_message 兜底。
    """
    default_message: str = "An unexpected error occurred. Please try again later."

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)
```

### 2.2 业务子类设计原则

在 `AppException` 基础上，按**业务领域**划分子类，每个子类对应一类故障场景。
**具体划分由 Agent 根据项目实际需要决定**，以下是划分思路：

- 识别项目中有哪些外部依赖（数据库、第三方 API、文件系统、消息队列等）
- 识别有哪些核心业务流程（数据处理、权限校验、资源查找等）
- 每个领域对应一个子类，覆盖该领域内所有可能的失败场景

```python
# 示例结构，具体子类名和 default_message 由项目决定
class SomeDomainError(AppException):
    default_message = "该领域操作失败，请稍后重试。"

class AnotherDomainError(AppException):
    default_message = "另一个领域的操作失败，请联系管理员。"
```

### 2.3 关键设计约束

- `default_message` 必须是**对用户安全、无内部细节**的文案
- 调用方传入 `message` 参数时可以覆盖为更具体的描述，但同样必须是用户安全的文案
- 不要用一个 `AppException` 包打天下——子类的**类型本身**是语义信息，handler 和日志可以据此区分处理

---

## 三、业务层的 raise 模式

在核心逻辑（非 API 层）中按以下模式处理异常：

```python
# ✅ 标准模式：捕获底层异常 → wrap 成领域异常 → raise
def some_core_operation(input):
    try:
        result = external_library.do_something(input)
        return result
    except SomeDomainError:
        raise  # 已经是领域异常，直接透传
    except Exception as exc:
        logger.error("operation_failed", {"input": input, "error": str(exc)}, exc=exc)
        raise SomeDomainError(f"Operation failed for '{input}'.") from exc


# ✅ 主动检测资源是否存在 → 直接 raise 带具体描述的异常
def get_resource(resource_id: str):
    row = db.query(resource_id)
    if row is None:
        raise NotFoundException(f"Resource '{resource_id}' does not exist.")
    return row


# ❌ 错误：在核心层 raise HTTPException（核心层不应知道 HTTP）
raise HTTPException(status_code=404, detail="not found")

# ❌ 错误：吞掉异常或以 None 作为错误信号
try:
    ...
except Exception:
    return None
```

---

## 四、全局 Handler 注册

在 `your_app/api/response.py` 中实现 `register_exception_handlers(app)`，
在 `main.py` 中的 FastAPI 实例创建后立即调用。

### 4.1 Handler 优先级（从高到低）

```
HTTPException          → 认证(401) / 权限(403) / 路由校验等 FastAPI 内置异常
AppException           → 已知业务异常，message 安全可暴露
RequestValidationError → Pydantic 请求体校验失败
Exception              → 兜底，完整记录日志，返回通用文案
```

### 4.2 完整实现

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from your_app.core.exceptions import AppException
from your_app.core import logger

_GENERIC_ERROR = "An unexpected error occurred. Please try again later."


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """将 FastAPI 内置 HTTPException 纳入统一响应信封。

        覆盖：认证(401)、权限(403)、不存在(404)，以及 router 中显式 raise 的 HTTPException。
        """
        logger.warning(
            "http_exception",
            {
                "method": request.method,
                "url": str(request.url),
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
        )
        return err(exc.detail if isinstance(exc.detail, str) else str(exc.detail))

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """处理已知业务异常，message 可直接暴露给客户端。"""
        logger.warning(
            "app_exception",
            {
                "method": request.method,
                "url": str(request.url),
                "error_type": type(exc).__name__,
                "message": exc.message,
            },
            exc=exc,
        )
        return err(exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理 Pydantic / FastAPI 请求体校验失败，不暴露内部 schema 细节。"""
        logger.warning(
            "request_validation_error",
            {
                "method": request.method,
                "url": str(request.url),
                "errors": exc.errors(),
            },
            exc=exc,
        )
        return err("Invalid request parameters. Please check your input and try again.")

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """兜底 handler：完整记录日志，只返回通用文案，绝不泄露内部细节。"""
        logger.error(
            "unhandled_exception",
            {
                "method": request.method,
                "url": str(request.url),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            exc=exc,
        )
        return err(_GENERIC_ERROR)
```

### 4.3 main.py 中的注册顺序

```python
app = FastAPI(...)

app.add_middleware(...)   # middleware 先注册

register_exception_handlers(app)  # ← 必须在 middleware 之后、include_router 之前

app.include_router(router_a)
app.include_router(router_b)
```

---

## 五、SSE / 流式接口的内联异常处理

SSE generator 在开始 yield 之后，全局 handler 无法再介入。
必须在 generator 内部捕获异常，通过 `err_message()` 提取安全文案后作为 SSE error 事件发出。

`err_message()` 定义在 `response.py` 中（详见响应信封规范）：

```python
def err_message(exc: Exception) -> str:
    """从任意异常提取客户端安全的错误描述。"""
    if isinstance(exc, AppException):
        return exc.message
    return _GENERIC_ERROR
```

SSE generator 中统一用单个 `except Exception` 分支处理，通过 `err_message()` 屏蔽分支差异：

```python
from your_app.api.response import err_message

async def event_generator():
    try:
        # ... 业务逻辑 ...
        yield sse_event({"type": "done"})
    except Exception as exc:
        log = logger.warning if isinstance(exc, AppException) else logger.error
        log("stream_exception", {"error_type": type(exc).__name__, "error": str(exc)}, exc=exc)
        yield sse_event({"type": "error", "message": err_message(exc)})
```

---

## 六、启动快速失败（Fail-Fast）

在 FastAPI lifespan 中，服务启动时校验所有必要的配置/环境变量，有缺失则立即退出：

```python
from contextlib import asynccontextmanager
import sys

@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = settings.validate()  # 返回缺失的变量名列表
    if missing:
        print(
            "[STARTUP ERROR] Missing required environment variables:\n"
            + "".join(f"  - {var}\n" for var in missing),
            file=sys.stderr,
        )
        sys.exit(1)

    # 初始化数据库、启动后台 worker 等
    yield
    # cleanup
```

---

## 七、日志级别规范

| 场景                                         | 级别      |
| -------------------------------------------- | --------- |
| 已知业务异常（`AppException` 子类）          | `WARNING` |
| 认证 / 权限失败（`HTTPException`）           | `WARNING` |
| 请求参数校验失败（`RequestValidationError`） | `WARNING` |
| 未知异常（兜底 `Exception`）                 | `ERROR`   |
| 流式接口中的已知业务异常                     | `WARNING` |
| 流式接口中的未知异常                         | `ERROR`   |

推荐使用结构化日志，异常 traceback 作为独立字段传入，不拼接进 message 字符串：

```python
# ✅ 推荐
logger.error("operation_failed", {"context": "..."}, exc=exc)

# ❌ 避免
logger.error(f"operation_failed: {traceback.format_exc()}")
```

---

## 八、禁止事项

- **禁止**在 API 层以外的代码中 raise `HTTPException`
- **禁止**在 handler 或 endpoint 里把 `str(exc)` 直接返回给客户端
- **禁止**在 SSE generator 里硬编码通用错误文案字符串，统一用 `err_message()`
- **禁止**在核心层吞掉异常（`except Exception: pass` 或静默返回 `None`）
- **禁止**在 lifespan 之外做配置校验，避免校验逻辑被遗漏

---

## 九、与响应规范的关系

本规范只负责**异常的捕获、分级和转化**。
`ok()` / `err()` 函数的格式定义参见《规范：统一 API 响应信封》。
两份规范配合使用，共同保证整个服务的错误处理行为一致且安全。
