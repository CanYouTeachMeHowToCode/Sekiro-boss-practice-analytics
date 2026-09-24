# Sekiro Boss Practice Analytics

[English](README.md) | 简体中文

一个用于记录《只狼：影逝二度》Boss 攻略尝试、失误以及玩家长期进步情况的 Web 应用。

## 为什么需要这个工具

只狼玩家经常卡在苇名弦一郎、剑圣 苇名一心、义父、破戒僧这样的 Boss 上，但大多数玩家并没有一种结构化的方式来了解：

* 哪些 Boss 招式或技能让自己死得最多
* 自己是否真的在进步
* 哪个阶段是主要瓶颈
* 击败每个 Boss 需要尝试多少次

Sekiro Boss Practice Analytics 把每一次 Boss 尝试转化为结构化的练习数据。

应用不要求玩家记住详细的战斗统计数据，而是只关注玩家在每次尝试后真正能回忆起来的信息，比如打到了哪个阶段、最后是被哪个招式击败的。

应用随后利用这些历史记录，识别反复出现的弱点和进步趋势。

---

## V1 — 手动记录的尝试分析

V1 是一个手动记录 Boss 尝试、并对失败原因进行分析的工具。

玩家记录每次打到了哪里、是什么结束了这次尝试，应用据此找出最常导致失败的招式和瓶颈阶段。

### V1.0 — 已完成

V1.0 以**苇名弦一郎**作为代表性 Boss，实现了完整的初始端到端流程。

V1 的目标刻意不追求覆盖所有只狼 Boss，而是在扩充数据之前，先验证完整的应用架构和用户流程。

### V1 功能

* 浏览已支持的只狼 Boss
* 查看 Boss 的阶段和招式
* 记录 Boss 尝试
* 记录这次尝试是胜利还是失败
* 记录打到的阶段
* 记录最终导致失败的 Boss 招式
* 当不确定是哪个招式时，支持选择 `Other`（其他）和 `Not Sure`（不确定）
* 为尝试添加可选备注
* 查看尝试历史
* 查看总尝试次数统计
* 找出最常导致失败的招式
* 找出主要瓶颈阶段
* 查看基础的进度分析

### V1 用户流程

```text
选择 Boss
    ↓
Boss 仪表盘
    ↓
记录尝试
    ↓
结果 + 到达阶段 + 失败招式
    ↓
保存尝试
    ↓
尝试历史
    ↓
失败分析
```

V1 刻意聚焦于一个小数据集和一条完整的纵向功能链路，而不是广泛的 Boss 覆盖。

---

## V2 — 结构化的只狼分析平台

### V2.0 — 已完成

V2 把 V1 原型扩展成了一个结构化、支持多个 Boss 的只狼练习分析平台。

V2 的主要变化，是从一个基于 JSON 的小型 MVP，转向一套能够支持多个 Boss 和更大量尝试历史的关系型持久化与分析架构。V1 的轻量记录表单保持不变：结果、到达阶段、失败招式 / `Other` / `Not Sure`，以及可选备注。

### V2 功能

#### PostgreSQL 持久化

用 PostgreSQL 取代了 V1 的 JSON 持久化层，ORM 使用 SQLAlchemy，schema 迁移使用 Alembic。

关系模型如下：

```text
Game（游戏）
 └── Boss
      ├── Phase（阶段）
      ├── Move（招式）
      └── Attempt（尝试）
           └── Failure Move（失败招式）

Phase ←── 多对多 ──→ Move
```

招式属于某个 Boss，即使出现在多个阶段，也只存储一份。另有一张关联表记录每个招式出现在哪些阶段以及顺序，因此死于同一个招式的尝试，无论发生在哪个阶段，都会指向同一条招式记录。

数据库约束和服务层校验会拒绝无效数据，比如属于其他 Boss 的失败招式、没有出现在所到达阶段的招式，或者带有失败原因的胜利记录。

Boss 数据保存在 `backend/seed/bosses.json` 中，后端每次启动时都会同步到 PostgreSQL，同步过程是幂等的。V1 的尝试历史通过一个单独的一次性导入脚本完成了迁移。

迁移过程中保留了 V1 的前端 API 契约。

#### 扩充 Boss 覆盖

V2 支持 8 个主要的只狼 Boss：

* 苇名弦一郎
* 义父
* 蝴蝶夫人
* 狮子猿
* 破戒僧（幻影）
* 宫内破戒僧
* 巨型忍者 枭
* 剑圣 苇名一心

不同 Boss 的阶段数和招式各不相同，但全部走同一套代码路径。Boss 卡片会同时显示英文名和中文名。

#### 更丰富的 Boss 数据

每个招式包含：

* 出现在哪些阶段
* 招式类型
* 攻击描述
* 前摇特征（来源中有描述时）
* 应对方式（counter）
* 常见失误（来源中有描述时）

#### 进度分析

在 V1 指标的基础上，每个 Boss 仪表盘新增了：

* 尝试进度图，展示每次尝试到达的阶段
* 全部历史与最近 10 次尝试的对比，分别按阶段和按招式统计失败次数
* 首次胜利前的尝试次数（包含获胜的那一次）

例如：

```text
                 全部历史   最近 10 次
飞渡浮舟            12          2
```

这表示记录到的、死于某个招式的失败正在变少。应用不会把它当作招式成功率来展示，因为应用并不知道这个招式实际出现了多少次。

并列的情况会如实显示为并列，而不会随意选出一个。

#### 只狼总览仪表盘

首页现在是一个游戏级别的仪表盘，展示：

* 挑战过的 Boss 数和已击败的 Boss 数
* 总尝试次数
* 练习最多的 Boss
* 首次胜利前需要最多尝试次数的 Boss
* 最近的练习活动（最近 7 天，以及所有 Boss 的最近 10 次尝试）
* Boss 对比表，包含尝试次数、最好成绩和是否击败

Boss 列表移到了 `/bosses`。

#### 数据溯源

每个 Boss 都记录了其招式数据来源的 Wiki 页面。招式细节取自这些来源，而不是凭空编造。

#### CI 与本地部署

每个 Pull Request 都会运行 4 个 GitHub Actions 任务，全部通过后才能合并进 `dev` 或 `main`：

* **backend：** 在 PostgreSQL 上运行 pytest，包括检查 SQLAlchemy 模型和 Alembic 迁移是否一致
* **frontend：** 类型检查、代码规范检查、单元测试和生产构建
* **integration：** 前端的 API 调用层连接真实的后端和 PostgreSQL 进行测试
* **docker：** 构建 Docker Compose 整套服务，并通过 nginx 进行冒烟测试

V2 使用 Docker Compose 在本地运行。

#### 推迟或跳过的内容

* **公网部署**移到了 V3：目前只有一个用户，而且在没有账号系统的情况下，公开的实例会让任何人都能新增攻略记录。V3 会加入账号系统，这个问题也就随之解决。
* **Boss 搜索和筛选**被跳过了，因为 8 个 Boss 在一个页面上就能放得下。

---

## 未来方向

长期路线图如下：

```text
V1
手动记录 Boss 尝试
+
基础失败分析

        ↓

V2
PostgreSQL
+
扩充的只狼 Boss 数据
+
更丰富的进度分析

        ↓

V3
用户账号
+
按用户区分的攻略记录
+
附带依据的练习建议
+
公网部署

        ↓

V4
实战录像分析
+
自动 / 半自动招式识别
+
详细的战斗表现指标

        ↓

V5
多游戏平台
+
只狼
+
黑神话：悟空
```

长期目标是把 Sekiro Boss Practice Analytics 从一个手动尝试记录工具，发展成一个通用的 Boss 练习与实战表现分析平台。

---

## 技术栈

### V1.0

* **后端：** FastAPI
* **持久化：** JSON
* **前端：** React + TypeScript
* **部署：** Docker

V1 刻意使用 JSON 持久化，因为初始数据集很小，主要目标是验证完整的应用流程。

### V2.0

* **后端：** FastAPI
* **数据库：** PostgreSQL
* **ORM：** SQLAlchemy
* **数据库迁移：** Alembic
* **前端：** React + TypeScript
* **部署：** Docker Compose（本地）
* **CI：** GitHub Actions

---

## 本地运行

需要安装 [Docker](https://www.docker.com/)（Windows 或 macOS 上用 Docker Desktop）。

1. 创建环境变量文件，并设置数据库密码：

   ```bash
   cp .env.example .env
   ```

   把 `.env` 里所有的 `change-me` 都替换成同一个密码。

2. 构建并启动所有服务：

   ```bash
   docker compose up -d --build
   ```

   后端每次启动时都会执行数据库迁移，并从 `backend/seed/bosses.json` 同步 Boss 数据。

3. 打开 http://localhost:8080 并注册一个账号。不登录也可以浏览 Boss 的招式，但记录尝试和查看分析需要登录。API 文档在 http://localhost:8000/docs。

在同一网络下用手机访问时，打开 `http://<电脑的局域网 IP>:8080`。Windows 上可以用 `ipconfig` 查看 IP，要看 Ethernet 或 Wi-Fi 网卡下面的地址，不是 `vEthernet (WSL)` 那一个。

攻略数据保存在名为 `postgres-data` 的 Docker 数据卷里。`docker compose down` 会保留数据；`docker compose down -v` 会把数据一起删除。

### 运行测试

后端测试和集成测试需要 PostgreSQL 正在运行（`docker compose up -d postgres`）。

```bash
# 后端：数据库测试从环境变量读取 TEST_DATABASE_URL，没有设置时会被跳过
cd backend
pip install -r requirements.txt
set -a; . ../.env; set +a   # 把 .env 加载到环境变量里（bash）
pytest

# 前端
cd frontend
npm ci
npm test
npm run test:integration   # 从 .env 读取 TEST_DATABASE_URL；需要后端的 Python 环境
```
