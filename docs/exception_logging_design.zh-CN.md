# 异常日志设计说明

本文档说明当前 `backend/docmind/core/logger.py` 中异常日志的设计目标, 取舍依据, 以及后续维护时必须注意的边界

---

## 1. 背景与问题

项目最早的异常日志实现有两个明显问题

1. 异常堆栈信息过长, 一条日志里同时出现完整 traceback 和多层重复异常信息, 阅读成本高
2. 当异常链较深时, 很难快速看出真正需要优先关注的业务代码位置

但如果为了“好读”而直接删掉原始 traceback, 又会带来另一个更严重的问题

1. 未来项目结构或异常包装方式发生变化时, 摘要字段可能不够完整
2. 一旦原始 traceback 被删掉, 排查时就失去了最原始的证据

因此日志系统不能只追求“短”, 也不能只保留“解释后的摘要”

---

## 2. 设计目标

当前异常日志设计同时满足两个目标

1. **保真**
   始终保留 Python 原始格式化得到的完整 traceback, 确保排查时有原始证据可回看
2. **提效**
   在原始 traceback 之外, 提供一组结构化摘要字段, 让开发者可以先快速定位到高概率有价值的位置

换句话说, 当前方案不是“用摘要替代原始堆栈”, 而是“原始堆栈 + 摘要双轨并存”

---

## 3. 当前日志结构

每条日志是一行 JSON, 基础壳结构如下

```json
{
  "ts": "...",
  "request_id": "...",
  "topic": "...",
  "data": { ... },
  "caller": {
    "file": "...",
    "line": 123,
    "func": "..."
  }
}
```

其中

- `caller` 表示谁调用了 `logger.debug/info/warning/error`
- 它不是异常抛出位置, 只是日志调用位置

当 `exc` 存在时, `data` 会在原业务字段基础上自动追加如下异常字段

- `error_type`
- `error`
- `traceback`
- `origin`
- `trigger`
- `call_chain`
- `ext_frames`
- `exception_chain`
- `root_cause`

---

## 4. 各字段的取值来源

这些字段都不是凭空猜测, 它们来自 Python 标准库 `traceback` 对异常对象自身 traceback 的提取结果

### 4.1 原始字段

#### `error_type`

来源

```python
type(exc).__name__
```

#### `error`

来源

```python
str(exc)
```

#### `traceback`

来源

```python
"".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
```

这是最重要的兜底字段, 它保留了 Python 原始完整异常堆栈, 包括 chained exceptions

### 4.2 摘要字段

摘要字段基于下面这一步得到的 traceback frame 列表

```python
frames = traceback.extract_tb(exc.__traceback__)
```

#### `origin`

含义

- 优先取“首个可见 app frame”
- 如果没有 app frame, 回退到首个 external frame

注意

- 它是“摘要视角下的起点”, 不是法证级定义的根因
- 当前实现会尽量剔除纯 catch-and-log 的那一层噪音帧

#### `trigger`

含义

- 优先取“最后一个可见 app frame”
- 如果没有 app frame, 回退到最后一个 external frame

包含字段

- `file`
- `line`
- `func`
- `code`

其中 `code` 直接来自 traceback frame 的 `line`

#### `call_chain`

含义

- 当前摘要视角下, 从外到内的简化调用链
- 格式为 `"file:line func"`

#### `ext_frames`

含义

- 被判定为 external 的 traceback frames 摘要
- 用于保留第三方库调用路径, 同时避免主 `call_chain` 过长

#### `exception_chain`

含义

- 只保留子异常链摘要, 不重复顶层异常本体
- 目的是减少重复信息

#### `root_cause`

含义

- 记录异常链最底层异常的 `error_type` 和 `error`
- 只是便于快速浏览的摘要

---

## 5. 为什么要判断“是不是业务代码”

如果不区分 app frame 和 external frame, 那么摘要字段通常会退化成“框架内部调用摘要”

具体问题包括

1. `origin` 很可能指向 FastAPI / Starlette / httpx / qdrant client 内部
2. `trigger` 也可能停留在第三方库内部抛错点
3. `call_chain` 可能大部分都是框架层代码, 人类阅读价值不高

因此, 只要希望 `origin` / `trigger` / `call_chain` 更偏向自己的业务代码, 就必须做一层 internal vs external 的区分

注意这里的取舍

1. **原始 traceback 不需要任何判断**
   它本身就是最原始证据
2. **摘要字段必须依赖判断**
   否则它们就不能起到“快速看懂业务位置”的作用

---

## 6. 当前是如何判断 app frame 的

当前逻辑基于项目根目录做判断

```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
Path(filename).resolve().is_relative_to(_PROJECT_ROOT)
```

含义是

- traceback frame 对应的文件如果位于当前后端项目根目录之下, 就认为是 app frame
- 否则认为是 external frame

这是一个“面向当前仓库结构的启发式规则”, 不是 Python 语言层面绝对客观的定义

---

## 7. 为什么这个判断可能受项目结构影响

因为“是不是业务代码”本质上不是 traceback 自带的事实, 而是我们基于目录结构做出的解释

只要下列结构假设成立, 当前摘要字段就比较稳定

1. `backend/docmind/core/logger.py` 仍然位于当前这个层级
2. 后端业务代码仍然位于当前推导出的项目根目录之下
3. 需要被视为“项目内代码”的模块, 没有被搬到仓库外部或作为第三方安装路径运行

如果未来出现下面这些变化, 摘要字段准确度可能下降

1. 把 `backend/docmind/core/logger.py` 挪到别的层级
2. 把一部分业务代码拆到当前项目根目录之外
3. 把内部共享代码以 site-packages / editable install / 外挂包路径运行
4. 将后端代码拆成多个互相独立的源码根目录, 但 logger 仍只认一个根

受影响的字段主要是

- `origin`
- `trigger`
- `call_chain`
- `ext_frames`
- `exception_chain` 里的同名字段

**不会因此失真的字段**

- `traceback`
- `error_type`
- `error`
- `root_cause.error_type`
- `root_cause.error`

也就是说, 项目结构变化影响的是“摘要解释层”, 不是“原始异常证据”

---

## 8. 为什么仍然保留摘要字段

原因很简单: 原始 traceback 虽然最完整, 但并不好扫读

在日常排查里, 摘要字段有两个明显价值

1. 第一眼就能看到最值得优先关注的业务位置
2. 不需要先通读一大段 traceback 才能定位大致落点

因此当前决策不是“摘要和原始 traceback 二选一”, 而是

1. `traceback` 负责保真
2. `origin/trigger/call_chain/...` 负责提效

---

## 9. 去重策略

为了避免回到最初“异常日志过于重复”的问题, 当前实现做了两层去重

1. 顶层异常只保留一份完整 `traceback`
2. `exception_chain` 只记录子异常链摘要, 不再把顶层异常再重复展开一遍

这样既保留了完整证据, 又避免最外层异常信息被结构化字段重复复制一次

---

## 10. 决策依据

这次实现采取当前方案, 基于以下判断

1. 只保留摘要字段不安全
   原始 traceback 一旦删除, 将来摘要判断失准时会直接影响排查能力
2. 只保留原始 traceback 可读性不够
   实际排查效率较低
3. 当前仓库短期内不会频繁重构目录结构
   因此用项目根目录作为 app frame 判断依据是可以接受的
4. 即使未来结构变化, 只要原始 traceback 仍在, 排查能力就不会根本丢失

---

## 11. 维护注意事项

后续维护这套日志时, 请遵守以下约束

1. **不要删除 `traceback`**
   这是最终兜底证据
2. **不要把摘要字段当成绝对事实**
   它们是“便于阅读的解释层”, 不是原始证据本身
3. **如果调整后端目录结构, 要同步评估 `_PROJECT_ROOT` 判定是否仍然成立**
4. **如果未来后端代码有多个源码根, 应将“app frame roots”改为显式配置列表**
5. **如果需要进一步减少日志体积, 优先压缩摘要字段, 不要优先删原始 traceback**

---

## 12. 如果未来确实要改项目结构

如果未来后端代码不再满足“单一项目根目录”假设, 推荐升级为显式配置方案, 例如

- `LOG_APP_FRAME_ROOTS`
- 或内部模块前缀白名单

这样 logger 不再依赖固定目录层级推断“哪些 frame 属于业务代码”, 而是通过配置维护规则

但无论未来怎么升级, 一个原则不应改变

**原始 traceback 必须始终保留**

