# 状态机工作流详解

## 1. 这篇文档要说明什么

很多人第一次接触 LangGraph 或类似工作流框架时，会有一个很自然的疑问：

“这不就是把几个函数按顺序调用吗？”

这个疑问在简单线性流程里并不奇怪。真正的区别出现在下面这些情况：

- 流程里有很多中间结果要传来传去
- 一个步骤执行完后，要根据结果决定走哪条分支
- 后续要插入新步骤
- 失败路径和成功路径都很多

状态机的价值，主要就在这里

## 2. 先用一个真实例子

假设我们要实现一个“订单履约”流程：

1. 校验订单
2. 如果金额太大，先人工审核
3. 检查库存
4. 如果库存不足，直接结束
5. 如果库存充足，继续扣款
6. 如果扣款失败，直接结束
7. 如果扣款成功，创建发货单

这个例子既有线性步骤，也有条件分支，很适合对比普通写法和状态机写法。

## 3. 普通编排方式

普通写法通常是一个主函数负责整个流程。

```python
def process_order(
    order: Order,
    user_id: str,
    tenant_id: str,
    coupon: str | None,
) -> dict:
    valid, reason = validate_order(order, user_id, tenant_id)
    if not valid:
        return {"status": "rejected", "reason": reason}

    needs_manual_review = order.amount > 10000
    if needs_manual_review:
        review_passed = manual_review(order, user_id, tenant_id)
        if not review_passed:
            return {"status": "rejected", "reason": "review_failed"}

    stock_available, inventory_reservation = check_inventory(
        order,
        tenant_id,
        coupon,
    )
    if not stock_available:
        return {"status": "rejected", "reason": "out_of_stock"}

    payment_success, payment_attempts = charge_payment(
        order,
        user_id,
        coupon,
    )
    if not payment_success:
        return {"status": "rejected", "reason": "payment_failed"}

    shipment = create_shipment(
        order,
        tenant_id,
        inventory_reservation,
    )
    return {
        "status": "success",
        "shipment_id": shipment.id,
        "payment_attempts": payment_attempts,
    }
```

### 3.1. 这种方式的问题是什么

这个函数不是不能用。问题是流程一旦复杂，主函数会开始承担太多职责。

它既要处理业务步骤，又要管理流程控制，还要搬运上下文。

### 3.2. 主函数要手动管理参数和返回值

主函数必须自己知道：

- `validate_order` 需要哪些参数
- `check_inventory` 返回了哪些值
- `inventory_reservation` 后面还要不要继续传
- `charge_payment` 的结果谁还会用到

也就是说，主函数成了参数和返回值的中转站。

随着流程复杂，主函数里会出现越来越多这种中间变量：

- `needs_manual_review`
- `review_passed`
- `stock_available`
- `inventory_reservation`
- `payment_success`
- `payment_attempts`
- `shipment`
- `reason`

这些变量不是业务核心本身，而是流程现场信息。普通方式里，这些信息往往要靠主函数手动接住、保存、再传给后续步骤。

### 3.3. 主函数还要负责分支判断

比如这一段：

```python
stock_available, inventory_reservation = check_inventory(order, tenant_id, coupon)
if not stock_available:
    return {"status": "rejected", "reason": "out_of_stock"}

payment_success, payment_attempts = charge_payment(order, user_id, coupon)
```

这里一段代码里同时发生了三件事：

1. 调用库存检查
2. 接住库存检查的返回值
3. 根据返回值决定下一步是结束还是去扣款

也就是说：

- “做库存检查”
- “判断库存不足时去哪”

被写在了一起。

### 3.4. 流程越复杂，主函数越像编排脚本

如果再增加需求：

- 海外订单先做风控
- 高风险订单要二次人工审核
- 扣款失败允许重试一次
- 发货失败要自动退款

那主函数只会继续膨胀，`if/else` 会越来越多，步骤处理和流程编排会更难分开。

## 状态机方式

状态机并不是“没有分支”，也不是“只能写固定顺序”。

它做的事情是把流程拆成三部分：

1. 用共享状态保存流程现场
2. 节点只负责处理状态
3. 图或路由负责决定下一步去哪

### 4.1. 第一步：定义共享状态

```python
from typing import TypedDict


class OrderState(TypedDict, total=False):
    order: Order
    user_id: str
    tenant_id: str
    coupon: str | None

    valid: bool
    reason: str
    needs_manual_review: bool
    review_passed: bool

    stock_available: bool
    inventory_reservation: str

    payment_success: bool
    payment_attempts: int

    shipment: Shipment
    status: str
```

这份 `state` 的意义很重要：

- 它保存的是整个流程的现场信息
- 后续节点共享并实时更新这份状态
- 节点不再依赖主函数逐个传参

这就是“共享状态”的真实含义。

普通方式里，主函数要手动搬运这些信息。  
状态机里，这些信息统一放在 `state` 里，由节点读写。

### 4.2. 第二步：节点只负责处理

节点的职责很单纯：读取状态，做一件事，把结果写回状态。

```python
def validate_order_node(state: OrderState) -> dict:
    valid, reason = validate_order(
        state["order"],
        state["user_id"],
        state["tenant_id"],
    )
    return {
        "valid": valid,
        "reason": reason,
        "needs_manual_review": state["order"].amount > 10000,
    }
```

```python
def manual_review_node(state: OrderState) -> dict:
    review_passed = manual_review(
        state["order"],
        state["user_id"],
        state["tenant_id"],
    )
    return {"review_passed": review_passed}
```

```python
def check_inventory_node(state: OrderState) -> dict:
    stock_available, inventory_reservation = check_inventory(
        state["order"],
        state["tenant_id"],
        state["coupon"],
    )
    return {
        "stock_available": stock_available,
        "inventory_reservation": inventory_reservation,
    }
```

```python
def charge_payment_node(state: OrderState) -> dict:
    payment_success, payment_attempts = charge_payment(
        state["order"],
        state["user_id"],
        state["coupon"],
    )
    return {
        "payment_success": payment_success,
        "payment_attempts": payment_attempts,
    }
```

```python
def create_shipment_node(state: OrderState) -> dict:
    shipment = create_shipment(
        state["order"],
        state["tenant_id"],
        state["inventory_reservation"],
    )
    return {
        "shipment": shipment,
        "status": "success",
    }
```

```python
def reject_node(state: OrderState) -> dict:
    return {
        "status": "rejected",
        "reason": state.get("reason", "rejected"),
    }
```

这里要特别注意：

- `check_inventory_node` 只负责把 `stock_available` 写进状态
- `charge_payment_node` 只负责把 `payment_success` 写进状态
- 它们不决定下一步去哪

这就是“node 只负责处理”的意思。

### 4.3. 第三步：用路由根据状态切换分支

这是状态机最关键的地方。

节点执行完之后，流程不是只能走固定下一步。  
它完全可以根据当前状态里的值，走不同的分支。

比如：

```python
def route_after_validation(state: OrderState) -> str:
    if not state["valid"]:
        return "reject"
    if state["needs_manual_review"]:
        return "manual_review"
    return "check_inventory"
```

```python
def route_after_review(state: OrderState) -> str:
    if not state["review_passed"]:
        return "reject"
    return "check_inventory"
```

```python
def route_after_inventory(state: OrderState) -> str:
    if not state["stock_available"]:
        return "reject"
    return "charge_payment"
```

```python
def route_after_payment(state: OrderState) -> str:
    if not state["payment_success"]:
        return "reject"
    return "create_shipment"
```

这里返回的：

- `"reject"`
- `"manual_review"`
- `"check_inventory"`
- `"charge_payment"`
- `"create_shipment"`

都是“节点名字”。

也就是说，路由函数返回的是“下一个要执行的节点名”。

### 4.4. 第四步：真正的编排代码

前面的节点代码和路由代码只说明了“每一块做什么”。  
真正把流程串起来的，是 graph 编排代码。

```python
from langgraph.graph import END, StateGraph


graph = StateGraph(OrderState)

# 第一个参数就是节点的名字, 与上面每个 router 返回的一一对应
# 这里只是添加节点 让 langgraph 知道有哪些节点可以执行
# 后面 graph.add_conditional_edges 才是定义节点执行完后的跳转规则（根据 state 动态决定下一步去哪）
# 这就是把顺序, 编排逻辑抽象出来了, 节点只负责处理事情, 不负责判断下一步去干嘛
graph.add_node("validate_order", validate_order_node)
graph.add_node("manual_review", manual_review_node)
graph.add_node("check_inventory", check_inventory_node)
graph.add_node("charge_payment", charge_payment_node)
graph.add_node("create_shipment", create_shipment_node)
graph.add_node("reject", reject_node)

graph.set_entry_point("validate_order")

graph.add_conditional_edges("validate_order", route_after_validation)
graph.add_conditional_edges("manual_review", route_after_review)
graph.add_conditional_edges("check_inventory", route_after_inventory)
graph.add_conditional_edges("charge_payment", route_after_payment)

graph.add_edge("create_shipment", END)
graph.add_edge("reject", END)

order_graph = graph.compile()
```

这段代码说明了一件很重要的事：

- 状态机不只是定义固定顺序
- 它也可以定义条件分支

比如这句：

```python
graph.add_conditional_edges("check_inventory", route_after_inventory)
```

它的意思是：

1. 先执行 `check_inventory`
2. 执行完后，读取最新的 `state`
3. 调用 `route_after_inventory(state)`
4. 如果返回 `"reject"`，就跳到 `reject`
5. 如果返回 `"charge_payment"`，就跳到 `charge_payment`

所以，状态机完全可以做到：

“一个节点执行完后，根据结果进入不同边”

## 5. 用同一个分支点做普通方式和状态机方式对比

下面只看“库存检查之后怎么走”。

### 5.1. 普通方式

```python
stock_available, inventory_reservation = check_inventory(order, tenant_id, coupon)
if not stock_available:
    return {"status": "rejected", "reason": "out_of_stock"}

payment_success, payment_attempts = charge_payment(order, user_id, coupon)
```

这一段里，主函数同时负责：

- 调用节点
- 接返回值
- 保存中间结果
- 做分支判断
- 决定下一步去哪

### 5.2. 状态机方式

节点：

```python
def check_inventory_node(state: OrderState) -> dict:
    stock_available, inventory_reservation = check_inventory(
        state["order"],
        state["tenant_id"],
        state["coupon"],
    )
    return {
        "stock_available": stock_available,
        "inventory_reservation": inventory_reservation,
    }
```

路由：

```python
def route_after_inventory(state: OrderState) -> str:
    if not state["stock_available"]:
        return "reject"
    return "charge_payment"
```

编排：

```python
graph.add_conditional_edges("check_inventory", route_after_inventory)
```

这里职责被明确拆开了：

- 节点负责把结果写进共享状态
- 路由负责根据状态决定分支
- graph 负责把这个分支规则接到流程图上

这就是状态机处理分支的方式。

## 6. 普通方式和状态机方式的核心差别

### 6.1. 普通方式

- 主函数负责整个流程
- 主函数手动管理参数传递和返回值接续
- 主函数同时承担步骤处理和流程编排
- 分支通常写在主函数的 `if/else` 中
- 流程越复杂，主函数越容易膨胀

### 6.2. 状态机方式

- 所有节点共享同一份 `state`
- 节点从 `state` 读取数据，并把结果写回 `state`
- 节点只负责处理，不负责全局流转
- 路由负责根据 `state` 决定下一步去哪
- graph 负责声明节点和边
- 分支被表达为显式的条件边

## 7. 状态机的核心价值

### 7.1. 共享状态

这是最直接的价值。

普通方式里，主函数要不断接住返回值、保存中间变量、再把它们传给后面的函数。  
状态机方式里，节点共享一份 `state`，不需要主函数做大量上下文搬运。

### 7.2. 处理和编排分离

节点负责做事。  
路由和 graph 负责流程流转。

这让每一层的职责更清晰。

### 7.3. 分支能力是显式的

状态机不是只能走固定顺序。

它既可以写：

- 固定边：`A -> B`

也可以写：

- 条件边：`A -> 根据 state 走 B 或 C`

这让复杂流程更容易表达。

### 7.4. 更容易扩展

如果后面要在“检查库存”和“扣款”之间插入一个“风控节点”：

普通方式通常要去改主函数的核心控制逻辑。  
状态机方式通常是：

1. 新增一个节点
2. 修改某个路由

原有节点本身往往不需要改很多。

## 8. 什么时候没必要上状态机

如果流程满足下面这些条件，普通函数编排通常就够了：

- 步骤很少
- 没有复杂分支
- 中间上下文不多
- 后续扩展概率低

这时直接写函数往往更简单

### 8.1. 一个更本质的判断信号

除了流程复杂度，还有一个更根本的问题可以帮助判断：

相同的输入，在不同的处理阶段，含义会不同吗？

如果答案是"会"，状态机通常是合适的。
如果答案是"不会"，状态机很可能是过度设计。

举个对比：

- 词法分析器：遇到 `"` 这个字符，在"普通文本"状态下意味着"进入字符串"，在"字符串内部"状态下意味着"结束字符串"。同一个输入，不同状态下含义完全不同 → 状态机合适
- Markdown 段落打包器：遇到一个段落块，不管当前积累了多少内容，处理逻辑都一样（header 就更新上下文，content 就追加进篮子）。输入的处理方式不依赖"当前处于哪个阶段" → 状态机不合适，用积累器就够了

这个信号比"步骤多不多""分支多不多"更根本：它关注的是"上下文是否改变了对输入的解释方式"，而不只是"流程是否复杂"

### 8.2. 状态机本身也有成本

状态机的价值是真实的，但引入它也有代价：

- 需要显式定义状态枚举和转移规则，代码量增加
- 阅读时需要同时理解节点、路由、graph 三层结构
- 对于简单流程，反而比直接写函数更难看懂

所以它是一个权衡，不是"更高级就更好", 判断标准始终是：这个流程的复杂度，是否真的需要用状态机来管理？

## 9. 结论

状态机的价值，不是把判断消灭掉，而是把流程组织得更清楚：

- `state` 负责承载上下文
- node 负责处理状态
- route 负责根据状态选择分支
- graph 负责把整个流程编排起来

所以它和普通函数编排的真正差别不是“能不能跑”，而是：

- 普通方式更像写一个大流程函数
- 状态机方式更像搭一个可维护、可扩展的流程系统

除了 状态机 还有个 dispatch table

```python
from enum import Enum, auto

class BlockType(Enum):
    HEADER = auto()
    CONTENT = auto()
    # 将来可以加 TABLE / FRONTMATTER / HTML_COMMENT 等

def classify_block(block: str) -> BlockType:
    if re.match(r"^#{1,6}\s+", block):
        return BlockType.HEADER
    return BlockType.CONTENT
  
def _handle_header(block: str, ctx: ChunkContext) -> None:
    ctx.flush()
    level = len(re.match(r"^(#+)", block).group(1))
    header_text = block.lstrip("#").strip()
    # 清除同级及以下 header
    ctx.headers = {k: v for k, v in ctx.headers.items()
                   if int(k.split("_")[1]) < level}
    ctx.headers[f"header_{level}"] = header_text

def _handle_content(block: str, ctx: ChunkContext) -> None:
    restored = _restore_fenced_block_placeholders(block, ctx.code_blocks)
    block_len = len(restored)
    if block_len > ctx.max_size:
        raise ValueError(...)
    if ctx.current_len > 0 and ctx.current_len + block_len + 2 > ctx.target_size:
        ctx.flush()
    ctx.texts.append(restored)
    ctx.current_len += block_len + (2 if len(ctx.texts) > 1 else 0)

HANDLERS: dict[BlockType, Callable] = {
    BlockType.HEADER:  _handle_header,
    BlockType.CONTENT: _handle_content,
}

for block in raw_blocks:
    block_type = classify_block(block)
    HANDLERS[block_type](block, ctx)
```