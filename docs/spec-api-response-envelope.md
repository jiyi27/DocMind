# 规范: 统一 API 响应信封 (Unified API Response Envelope)

> 本文档描述一套适用于内部 Web 服务的统一 API 响应机制, 
> AI Agent 在实现新项目时, 应严格参照本规范构建响应层

---

## 一, 核心思想

**所有 HTTP 响应, 无论成功还是失败, 均返回同一个 JSON 结构 (信封), HTTP 状态码始终为 200, **
客户端只需检查 `code` 字段, 无需处理多种 HTTP 状态码分支

这种设计适用于: 
- 内部系统 / BFF(Backend for Frontend)
- 前端与后端由同一团队维护
- 不需要对外开放的 REST API

---

## 二, 响应信封格式

```json
// 成功
{
  "code": 0, 
  "message": "ok", 
  "data": { ... }
}

// 失败
{
  "code": -1, 
  "message": "对用户安全的错误描述", 
  "data": null
}
```

| 字段 | 类型 | 说明 |
| --------- | ------------- | ------------------------------------------------------ |
| `code` | `int` | `0` = 成功, `-1` = 失败 |
| `message` | `str` | 成功时为 `"ok"` 或业务描述, 失败时为面向用户的安全文案 |
| `data` | `any \| null` | 成功时携带业务数据, 失败时为 `null` |

---

## 三, 实现 (FastAPI / Python)

### 3.1 辅助函数

在 `your_app/api/response.py` 中实现以下函数, **整个项目所有 endpoint 均通过这两个函数返回响应, 禁止直接使用 `JSONResponse` 或 `dict`**

```python
from typing import Any
from fastapi.responses import JSONResponse

_GENERIC_ERROR = "An unexpected error occurred. Please try again later."


def ok(data: Any = None, message: str = "ok") -> JSONResponse:
    """构建成功响应, """
    return JSONResponse(
        status_code=200, 
        content={"code": 0, "message": message, "data": data}, 
    )


def err(message: str, data: Any = None) -> JSONResponse:
    """构建失败响应, """
    return JSONResponse(
        status_code=200, 
        content={"code": -1, "message": message, "data": data}, 
    )
```

### 3.2 在 Endpoint 中使用

```python
# ✅ 正确
@router.post("/items")
async def create_item(body: ItemCreate):
    item = await service.create(body)
    return ok(data=item.model_dump(), message="Item created")

# ✅ 正确: 失败时直接 raise, 由全局 handler 统一转为 err()
@router.get("/items/{id}")
async def get_item(id: int):
    item = await service.get(id)
    if not item:
        raise NotFoundException(f"Item {id} not found")
    return ok(data=item.model_dump())

# ❌ 错误: 手动返回裸 dict 或裸 JSONResponse
return {"code": 0, "data": item}
return JSONResponse(content={"error": "not found"}, status_code=404)
```

### 3.3 SSE / 流式接口的辅助函数

流式接口 (SSE) 无法使用全局 exception handler, 需要在 generator 内部捕获异常, 
提供 `err_message(exc)` 函数统一提取安全文案, **避免在 generator 里硬编码字符串**

```python
from your_app.core.exceptions import AppException

def err_message(exc: Exception) -> str:
    """从任意异常提取客户端安全的错误描述, 供 SSE generator 使用, """
    if isinstance(exc, AppException):
        return exc.message
    return _GENERIC_ERROR
```

SSE generator 中的使用模式

```python
async def event_generator():
    try:
        # ... 业务逻辑 ...
        yield sse_event({"type": "done"})
    except Exception as exc:
        log = logger.warning if isinstance(exc, AppException) else logger.error
        log("stream_exception", {"error": str(exc)}, exc=exc)
        yield sse_event({"type": "error", "message": err_message(exc)})
```

---

## 四, 目录约定

| 文件 | 职责 |
| --------------------------- | ------------------------------------------------------------------------------ |
| `your_app/api/response.py` | 定义 `ok()`, `err()`, `err_message()`, `_GENERIC_ERROR`, 全局 handler 注册函数 |
| `your_app/api/routers/*.py` | 只调用 `ok()` / `err()`, 不直接使用 `JSONResponse` |
| `your_app/api/main.py` | 调用 `register_exception_handlers(app)` 完成注册 |

---

## 五, 禁止事项

- **禁止**在 router 文件里直接 `return JSONResponse(...)`
- **禁止**在 router 文件里构造 `{"code": ..., "data": ...}` 的裸 dict
- **禁止**在 SSE generator 里硬编码 `"An unexpected error occurred..."` 字符串, 使用 `err_message()` 替代
- **禁止**为不同类型的错误返回不同的 HTTP 状态码 (一律 200, 靠 `code` 区分)

---

## 六, 与异常处理规范的关系

本规范只负责**响应格式的构造**, 不负责异常的捕获和分级处理, 
异常如何被捕获, 如何转化为 `err()` 响应, 参见《规范: 异常处理与全局 Handler》, 
两个规范配合使用, 共同保证每个 HTTP 响应都走统一信封
