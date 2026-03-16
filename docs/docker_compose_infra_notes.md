# Backend Docker Compose 问题说明

这份文档专门解释这次 `backend/` 目录下 Docker Compose 基础设施报错的原因。

重点不是记住几个命令，而是先搞清楚下面这几个概念：

- 什么是 Docker 的“全局容器名”
- 什么是 Docker Compose 的“项目”和“服务”
- `docker exec` 和 `docker compose exec` 的根本区别
- 为什么 `container_name` 会把事情变复杂
- 为什么这次会出现“容器冲突”和“模型像是丢了”的现象

---

## 1. 先讲最基础的概念

### 1.1 Docker 本身管理的是“容器”

如果只看 Docker，不看 Compose，那么 Docker 主要管理的是一个个具体的容器。

比如你执行：

```bash
docker ps -a
```

你看到的是一批容器，每个容器都有：

- 容器 ID
- 镜像
- 状态
- 名字

这里的“名字”是 Docker 全局范围内的名字。

也就是说，如果已经有一个容器叫 `ollama`，那么你不能再创建第二个也叫 `ollama` 的容器。

这个名字不是“当前项目里的名字”，而是“整台机器上的唯一名字”。

---

### 1.2 Docker Compose 管理的是“项目里的服务”

Compose 比 Docker 多了一层抽象。

在 `docker-compose.yml` 里，你写的是：

```yaml
services:
  ollama:
    image: ollama/ollama

  qdrant:
    image: qdrant/qdrant
```

这里的 `ollama` 和 `qdrant`，首先是 **service 名**，不是容器名。

Compose 的思路是：

1. 你先定义一个项目里的服务
2. Compose 再根据这个服务帮你创建真正的容器、网络、volume

如果你在 `backend/` 目录执行 `docker compose up -d`，Compose 会把当前目录当成一个项目，项目名通常是目录名，比如 `backend`。

于是 Compose 会自动生成类似这样的资源：

- 容器：`backend-ollama-1`
- 容器：`backend-qdrant-1`
- 网络：`backend_default`
- volume：`backend_ollama_data`
- volume：`backend_qdrant_storage`

注意这里有一个很重要的点：

`ollama` 是 service 名，`backend-ollama-1` 才是真正的容器名。

也就是说，Compose 帮你把“项目”和“服务”映射成真实的 Docker 资源。

---

### 1.3 所以，Compose 是“项目内寻址”，Docker 是“全局寻址”

可以这样理解：

- `docker ...` 操作的是 Docker 里真实存在的容器、网络、volume
- `docker compose ...` 操作的是“当前 compose 项目中的某个 service”

这两者不是一回事。

`docker` 看的是真实容器名。  
`docker compose` 看的是当前项目下的 service。

这正是你这次问题的核心。

---

## 2. `docker exec` 和 `docker compose exec` 的根本区别

这是这次最关键的一部分。

### 2.1 `docker exec`

例如：

```bash
docker exec ollama ollama pull nomic-embed-text:latest
```

这条命令的意思是：

“去找一个名字就叫 `ollama` 的容器，然后在里面执行 `ollama pull ...`。”

它有几个特点：

- 它只认“真实容器名”
- 它不关心这个容器是不是当前项目的
- 它不关心这个容器是不是由 Compose 创建的
- 只要全局里有一个容器名叫 `ollama`，它就会操作它

所以，`docker exec` 是典型的“全局寻址”。

它并不知道你现在在 `backend/` 目录，也不知道你心里想操作的是 `backend` 这个项目里的 Ollama 服务。

它只知道一件事：去找名字叫 `ollama` 的容器。

---

### 2.2 `docker compose exec`

例如：

```bash
docker compose exec ollama ollama pull nomic-embed-text:latest
```

这条命令的意思是：

“在当前 compose 项目里，找到 service 名为 `ollama` 的那个服务对应的容器，然后在里面执行命令。”

它有几个特点：

- 它认的是 service 名，不是全局容器名
- 它依赖当前目录下的 compose 项目
- 它会操作当前项目里的 `ollama` 服务，而不是整台机器上任意一个叫 `ollama` 的容器

所以，`docker compose exec` 是“项目内寻址”。

---

### 2.4 那么 `docker compose exec ollama ...` 是怎么知道要进哪个容器的

这是一个很常见的疑问。

比如这条命令：

```bash
docker compose exec ollama ollama pull nomic-embed-text:latest
```

很多人会想：

“可是我自己都不知道容器名，它怎么知道要把模型装到哪个容器里？”

答案是：  
它不是靠“猜容器名”来找目标的，而是靠 **当前 compose 项目 + service 名** 来找。

这里的 `ollama` 不是容器名，而是 `docker-compose.yml` 里的 service 名：

```yaml
services:
  ollama:
    image: ollama/ollama
```

`docker compose exec ollama ...` 的查找过程可以简单理解为：

1. 先看你当前所在目录的 compose 项目
2. 读取当前项目的 `docker-compose.yml`
3. 找到 service 名叫 `ollama` 的服务
4. 找到这个服务当前对应的运行中容器
5. 在那个容器里执行命令

所以我们不需要手动记住容器名。

---

### 2.5 那容器名是随机的吗

也不是随机的。

如果你不写 `container_name`，Compose 会按规则自动生成容器名，通常像这样：

```text
backend-ollama-1
backend-qdrant-1
```

这个名字通常由三部分组成：

- 项目名，例如 `backend`
- service 名，例如 `ollama`
- 实例序号，例如 `1`

所以它不是随机字符串，而是 Compose 自动生成的“项目化名字”。

只是我们通常不应该依赖这个名字来写脚本，因为：

- 它是 Compose 内部生成的结果
- 我们真正稳定依赖的应该是 service 名
- service 名才是 compose 配置里的逻辑标识

---

### 2.3 这两个命令为什么语义差很多

表面上看，这两条命令都像是在“进入 Ollama 容器执行 pull”：

```bash
docker exec ollama ...
docker compose exec ollama ...
```

但实际上它们找目标的方式完全不同：

- `docker exec ollama ...`：按容器名找，范围是全局
- `docker compose exec ollama ...`：按 service 名找，范围是当前 compose 项目

这就是根本区别。

如果你的机器上只有一个 Ollama 容器，而且永远不变，那这两个命令看起来好像差不多。

但一旦出现下面这些情况，差别就会非常大：

- 项目目录变了
- compose 项目名变了
- 有旧容器残留
- 同一台机器上跑过多个 Ollama
- 你手动删过、重建过容器

这时 `docker exec` 就很容易操作错对象，或者让你以为自己在操作“当前项目的服务”，实际上操作的是“另一只同名容器”。

---

## 3. `container_name` 为什么会制造问题

你之前的 compose 配置里有：

```yaml
container_name: ollama
container_name: qdrant
```

很多人第一次接触 Compose 时会觉得这很方便，因为以后就能直接：

```bash
docker exec ollama ...
```

但这其实是在“强行把 Compose 的 service，绑定成 Docker 的全局容器名”。

这会带来几个问题。

### 3.1 它破坏了 Compose 默认的项目隔离

正常情况下，Compose 会自动生成：

- `backend-ollama-1`
- `backend-qdrant-1`

这些名字天然带着项目前缀，不容易和别的项目冲突。

但你一旦写了：

```yaml
container_name: ollama
```

就相当于告诉 Docker：

“不管我属于哪个项目，我都必须叫 `ollama`。” 

这时候，容器名不再是项目内的，而变成了机器全局唯一资源。

---

### 3.2 旧容器即使停掉了，也仍然占名字

Docker 的规则是：

- 只要这个容器还存在
- 即使它是 `Exited`
- 它的名字也还被占着

所以如果机器上已经有一个旧容器叫 `ollama`，那么新的 compose 再去创建 `ollama`，就会直接冲突：

```text
Conflict. The container name "/ollama" is already in use
```

这也是你后面执行 `docker compose up -d` 时遇到的错误。

不是镜像有问题，不是 volume 有问题，而是 **名字先撞车了**。

---

### 3.3 它会诱导你一直用 `docker exec`

一旦你给容器固定了全局名字，人就很容易形成习惯：

```bash
docker exec ollama ...
```

但这样做会越来越偏离 Compose 的使用方式。

长期来看，就会出现这种情况：

- 你的容器是用 Compose 起的
- 你的 volume 是 Compose 管的
- 你的网络也是 Compose 管的
- 但你操作容器时，却绕过 Compose，直接按全局容器名去操作

这会让“当前项目到底在管谁”这件事越来越模糊。

---

## 4. 这次问题是怎么一步一步发生的

现在把这次现象串起来看，就比较容易懂了。

---

### 第一步：原来的 `infra-up` 用的是 `docker compose start`

原来 `Makefile` 里写的是：

```makefile
infra-up:
	docker compose start
```

这个命令适合“当前 compose 项目已经创建过容器，而且 Compose 还能正确识别到这些容器”的情况。

但是它 **不会创建新容器**。

如果当前项目找不到它认为应该存在的容器，就会报：

```text
service "qdrant" has no container to start
```

所以这条命令本身就偏脆弱。

---

### 第二步：你机器上又存在全局命名的旧容器

因为之前用了：

```yaml
container_name: ollama
```

所以机器上有一个真实容器名就叫 `ollama`。

哪怕它已经退出，只要容器还在，它就继续占着这个名字。

---

### 第三步：你尝试用 `docker compose up -d` 修复

这本来是对的，因为 `up -d` 比 `start` 更稳，它会：

- 没有容器时创建
- 有容器时启动或更新

但这时 Compose 需要创建新的 `ollama` 容器，而旧的全局容器名 `ollama` 还被占着，所以 Docker 拒绝创建：

```text
Conflict. The container name "/ollama" is already in use
```

于是你又遇到了第二层错误。

---

### 第四步：你手动删了旧容器

你删掉旧容器之后，名字冲突解决了，新容器终于可以创建。

但接下来你发现模型像是没了。

这通常不是因为 `docker rm` 自动删了 named volume，而更可能是：

- 旧容器挂的是旧 volume
- 新容器挂的是另一个 volume
- 新容器看到的是一块“空硬盘”

所以表面现象像“模型被删了”，实际上更像“模型还在别的 volume 里，但新容器没挂到原来那块 volume”

---

## 5. 为什么会出现“像是换了一块硬盘”的现象

Compose 的 volume 默认是带项目名前缀的。

比如从 `backend/` 目录运行时，可能得到：

- `backend_ollama_data`

如果你以前在别的项目名下运行过，比如项目名是 `docmind`，那可能还存在：

- `docmind_ollama_data`

这时就会出现一种很绕的情况：

- 你以为自己一直在用“同一个 Ollama”
- 但其实不同阶段的容器，挂载的是不同项目下的 volume

于是你删掉一个容器、再创建一个新容器后，看到的模型集合就可能不一样。

问题不一定是数据没了，而是“当前连上的不是原来那块数据盘”。

---

## 6. 这次是怎么修复的

这次修复做了三件事。

### 6.1 `infra-up` 改成 `docker compose up -d`

现在是：

```makefile
infra-up:
	docker compose up -d
```

它比 `start` 更适合开发环境，因为它是幂等的：

- 容器存在就启动
- 容器不存在就创建
- 重复执行通常没问题

这意味着 Docker Desktop 重启之后，你不需要赌“旧容器一定还能被当前 compose 识别到”。

---

### 6.2 `docker exec` 改成 `docker compose exec`

现在是：

```makefile
docker compose exec ollama ollama pull nomic-embed-text:latest
```

它的好处是：

- 始终操作当前 compose 项目的 Ollama 服务
- 不依赖某个全局容器名
- 不容易误操作旧容器或别的项目里的容器

也就是说，命令的“作用对象”终于和 Compose 项目是一致的了。

---

### 6.3 删除 `container_name`

删除之后，Compose 会恢复默认命名方式，例如：

- `backend-ollama-1`
- `backend-qdrant-1`

这样做的好处是：

- 避免全局名字冲突
- 保留 Compose 的项目隔离能力
- 让 `docker compose exec`、`docker compose up`、`docker compose stop` 这些命令始终围绕同一个项目工作

---

### 6.4 增加 `restart: unless-stopped`

现在服务里还加了：

```yaml
restart: unless-stopped
```

它的作用是：

- 如果 Docker daemon 重启，容器会自动尝试恢复
- 只要不是你主动 stop，它就会尽量重新起来

这不是根本修复，但能减少 Docker Desktop 重启后的手工操作。

---

## 7. 你应该怎么理解这次问题

这次问题的本质，不是单纯一句“Docker Desktop 重启后 compose 坏了”。

真正的问题是三件事叠在一起：

1. `infra-up` 用了比较脆弱的 `docker compose start`
2. compose 文件里用了全局的 `container_name`
3. 初始化命令又使用了全局寻址的 `docker exec`

这三件事叠在一起，就会导致整个系统同时存在两套思路：

- 一套是 Compose 的“项目内管理”
- 一套是 Docker 的“按全局容器名直接操作”

平时看起来能用，但一旦 Docker Desktop 重启、容器残留、项目名变化、或者你手动删容器，这套系统就很容易进入混乱状态。

---

## 8. 最后给一个最简单的记忆方式

你可以用下面这句话记住：

### `docker exec` 找的是“全局容器”
### `docker compose exec` 找的是“当前项目里的 service”

如果你的服务本来就是通过 Compose 管起来的，那么绝大多数时候都应该优先用：

```bash
docker compose ...
```

而不是：

```bash
docker ...
```

尤其不要再依赖这种固定全局容器名的写法：

```yaml
container_name: ollama
```

因为它看起来方便，实际上会把 Compose 的项目边界打乱。

---

## 9. 当前推荐用法

在 `backend/` 目录下执行：

首次初始化：

```bash
make infra-init
```

日常拉起基础设施：

```bash
make infra-up
```

如果你是“直接退出了 Docker Desktop，然后重新打开”，最推荐执行的也是这一条：

```bash
cd backend
make infra-up
```

原因是现在 `make infra-up` 实际执行的是：

```bash
docker compose up -d
```

这个命令比较稳，因为它会尽量把当前项目恢复到正确状态：

- 容器在运行中：通常不会报错
- 容器停止了：会启动
- 容器不存在：会创建
- 重复执行：通常也是安全的

所以它不是“只负责启动已有容器”，而是“让当前 compose 项目回到应该运行的状态”。

停止基础设施：

```bash
make infra-down
```

如果以后需要进入 Ollama 容器执行命令，也优先用：

```bash
docker compose exec ollama <command>
```

而不是：

```bash
docker exec ollama <command>
```

---

## 10. 一句话总结

这次问题的根源是：  
**一个本来应该完全由 Docker Compose 按“项目”管理的系统，被 `container_name` 和 `docker exec` 拉回了“按全局容器名操作”的模式。**

一旦 Docker Desktop 重启、旧容器残留、或者容器重建，这两套模型就会互相打架，于是你就看到了：

- `has no container to start`
- `container name is already in use`
- 模型像是“消失了”

修复的核心，就是把整个工作流重新统一回 Compose 的项目模型里。
