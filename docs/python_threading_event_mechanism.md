## 1. 概念解释

### 1.1. `threading.Thread`

```python
import threading

def foo():
    # 循环执行任务
    while ....

# 创建一个线程实例 t, 负责执行这个任务 foo
t = threading.Thread(target=foo)
t.start() # 开始执行任务 foo

print("主线程执行...")
```

### 1.2. `threading.Event`

`threading.Event` 提供两件事

- 一个共享状态 (flag)`True / False`
- 一个等待这个状态的能力 `event.wait()`

核心 API 行为

| 方法 | 做什么 |
| ---------- | --------------------------- |
| `set()` | flag = True, 并唤醒等待线程 |
| `clear()` | flag = False |
| `wait()` | 如果 flag=False → 阻塞 |
| `is_set()` | 查看状态 |

> 误导: `threading.Event` 是一个线程间通信的开关 (同步原语), 它内部维护一个布尔标志: 
> False: 红灯 (路口堵住, 大家都得停下等待)
> True: 绿灯 (路口通行, 大家可以随意通过)
> 红绿灯"这个比喻入门好用, 但本质是有误导性的, 它让人误以为: Event 在"控制线程运行/停止", 但实际上 Event 不会控制线程, 它只是提供一个"条件", 线程自己决定是否等待这个条件, **Event = 一个"共享的条件标志" + "等待机制"**, 而不是控制器

### 1.3. Thread + Event: 怎么配合


```python
import threading
import time

class Worker:
    def __init__(self):
        self.poll_interval = 10 # 10s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        # 重置停止信号, 确保线程重新启动时不会立即退出 (Event 可能在上一次 stop() 后仍为 True)
        self._stop_event.clear() # Reset stop flag for a fresh start
        # 初始化线程对象, 可以看到线程对象不是在 init 函数被初始化的而是在这里
        # self._thread 是一个线程对象, 它被创建时, 领到的任务是"执行 _run"
        self._thread = threading.Thread(target=self._run)
        self._thread.start() # 线程开始工作执行

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        conn = self._connect()
        try:
            self._requeue_processing_jobs(conn)
            while not self._stop_event.is_set():
                job = self._claim_next_job(conn)
                if job is None:
                    # self._stop_event.wait() 本质上是一个可中断的 sleep (可以被提前唤醒)
                    # 最多等待 poll_interval 秒
                    # 如果 stop_event 被 set(), 则会提前返回
                    self._stop_event.wait(self.poll_interval)
                    continue

                self._process_job(conn, job)
        finally:
            conn.close()

# 使用
w = Worker()
w.start()
time.sleep(3)
w.stop() # 3 秒后优雅停止
```

这个 Worker 是可以 start → stop → 再 start 的, `start()` 里的第一行代码 `clear()` 是在保证每次 start 都是一个"干净状态"

> 工人 (_thread) 在执行 _run 时, 通过 self._stop_event 不断查看信号, 这也是当前 self._thread 线程怎么和 self._stop_event "关联"的, 本质上说不是关联, 是 self._thread 主动监听, self._stop_event 不负责主动通知某个线程, 只负责提供信号
> `Event` 是信号旗, `Thread` 是看旗的工人, 工人通过不断检查旗子状态, 自主决定何时停止, Event 不强制, 不杀死线程——它只提供信号, 响应是自愿的, 甚至逻辑可以反着来 无所谓, 只要你的代码逻辑对就行


**问题:** `self._stop_event.wait(self.poll_interval)` 执行后, 执行 `self._run()` 的线程是什么

```python
self._stop_event.wait(self.poll_interval)
```

等价于逻辑

```
if event_flag == True:
    立即返回 (不会阻塞)
else:
    阻塞, 直到: 
        - 被 set() 唤醒
        - 或 timeout 到期
```

线程处于阻塞 (Blocked) 状态, 操作系统层面等同于睡眠, 具体来说, `threading.Event.wait()` 底层是通过一个条件变量 (Condition Variable) 实现的

```
self._stop_event.wait(5.0)
    └─► condition.wait(timeout=5.0)
            └─► pthread_cond_timedwait() ← OS 系统调用
```

线程调用 pthread_cond_timedwait() 后会被操作系统挂起, 从调度队列中移除, 不占用任何 CPU, 直到

- 超时 (5 秒到了)→ OS 唤醒线程, 返回 False
- 被通知 (_stop_event.set() 触发)→ OS 唤醒线程, 返回 True

