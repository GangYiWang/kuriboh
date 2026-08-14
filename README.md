# 栗子杯 V1

栗子杯是面向《游戏王 Master Duel》玩家的赛事平台。当前已完成 **Phase 6：消息、首页、审计与 V1 收尾**。

## 项目结构

```text
Kuriboh/
├─ frontend/          Vue 3 + TypeScript 正式前端
├─ backend/           FastAPI + SQLAlchemy + Alembic 正式后端
├─ docs/              设计与里程碑文档
├─ static-preview/    已确认的静态视觉基线（保留，不参与正式运行）
└─ sites-preview/     历史预览包装（不是正式项目）
```

## 环境要求

- Node.js 22 或更高版本
- npm 10 或更高版本
- Python 3.11 或更高版本
- Docker Desktop（推荐，用于本地 PostgreSQL）或可访问的 PostgreSQL 17 实例

## 首次启动

以下命令均使用 Windows CMD 格式，并假设当前目录为项目根目录 `Kuriboh`。

### 1. 准备环境变量

在项目根目录复制示例文件：

```bat
copy /Y .env.example .env
```

示例配置只用于本地开发。部署前必须修改数据库密码，并确保 `.env` 不进入版本控制。

### 2. 启动 PostgreSQL

使用 Docker：

```bat
docker compose up -d postgres
docker compose ps
```

若使用已有 PostgreSQL，请在 `.env` 中修改 `DATABASE_URL`。应用同时接受标准 PostgreSQL URL 和显式 psycopg 驱动 URL：

```text
postgresql://用户:密码@主机:端口/数据库
```

标准 URL 会由配置层转换为 `postgresql+psycopg://`，统一使用项目安装的 psycopg 3 驱动。

### 3. 启动后端

```bat
cd /d backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[test]"
.venv\Scripts\python.exe -m alembic upgrade head
dev.cmd
```

Windows 开发环境推荐使用 `dev.cmd`，它会自动启用 UTF-8 并关闭日志颜色。其他平台可运行 `python -m app.dev`。

后端默认地址为 `http://127.0.0.1:8000`，开发环境接口文档位于 `http://127.0.0.1:8000/api/docs`。

### 4. 启动前端

另开终端：

```bat
cd /d frontend
npm install
npm run dev
```

前端默认地址为 `http://127.0.0.1:5173`。开发服务器会将 `/api` 请求转发到本地后端；首页显示“前后端服务已连接”即基础联通成功。

## 数据库迁移

从空数据库建立当前结构：

```bat
cd /d backend
.venv\Scripts\python.exe -m alembic upgrade head
```

查看当前版本和迁移历史：

```bat
cd /d backend
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic history
```

后续修改 SQLAlchemy 模型时，先生成并人工检查迁移，再执行升级：

```bat
cd /d backend
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
.venv\Scripts\python.exe -m alembic upgrade head
```

迁移历史：

- `20260813_0001`：Phase 0 空业务基线。
- `20260813_0002`：Phase 1 用户、禁卡表版本和公告。
- `20260813_0003`：Phase 2 赛事、报名状态和正式参赛名单快照。
- `20260813_0004`：Phase 3 瑞士轮、对局提交、排名快照、退赛和关键操作审计。
- `20260813_0005`：Phase 4 固定种子淘汰赛轮次、签表和对局种子字段。
- `20260813_0006`：Phase 5 赛事结束时间、四强卡组截图提交和不可变周报快照。
- `20260813_0007`：Phase 6 站内消息、人工通知去重键和赛事维度审计日志。

## 测试与构建

后端测试：

```bat
cd /d backend
.venv\Scripts\python.exe -m pytest
```

前端测试、类型检查和生产构建：

```bat
cd /d frontend
npm test
npm run type-check
npm run build
```

测试覆盖健康检查、统一错误结构、账号与权限、内容及文件上传安全、赛事与报名、瑞士轮完整规则、Top 2/4/8 淘汰赛、赛事结束与周报，以及 Phase 6 消息范围、重复通知保护、我的赛事和管理员审计权限。默认测试使用独立的内存数据库，不会修改开发数据库。

## API 基线

- `GET /api/health`：同时检查应用和数据库连接。
- `GET /api/admin/health`：管理员权限边界检查，仅 `TOURNAMENT_ADMIN` 可访问。
- 所有错误统一返回 `code`、`message`、`details` 和 `request_id`。
- 响应通过 `X-Request-ID` 返回请求追踪标识，日志使用结构化 JSON。

角色常量仅包含已确认的 `PLAYER` 与 `TOURNAMENT_ADMIN`。密码使用 Argon2 哈希，登录凭证使用带有效期的 JWT；管理员权限由后端依赖统一校验。

## 创建初始管理员

先完成迁移，再使用交互式命令创建管理员，避免把密码留在终端历史中：

```bat
cd /d backend
.venv\Scripts\python.exe -m app.cli create-admin --qq 你的QQ号 --nickname 你的昵称
```

程序会提示输入至少 8 个字符的密码。已有 QQ 号或昵称不会被覆盖。

## Phase 1～6 接口

- `/api/auth/register`、`/api/auth/login`、`/api/auth/me`、`/api/auth/change-password`
- `/api/auth/qq/status`、`/api/auth/qq/callback`、`/api/auth/qq/bind`
- `/api/banlists`、`/api/banlists/current`、`/api/banlists/{id}`
- `/api/announcements`、`/api/announcements/{id}`
- `/api/admin/banlists`、`/api/admin/announcements`
- `/api/admin/uploads/images`
- `/api/tournaments`、`/api/tournaments/{id}`
- `/api/tournaments/{id}/registrations`、`/api/tournaments/{id}/registrations/me`、`/api/tournaments/{id}/registrations/cancel`
- `/api/admin/tournaments`、`/api/admin/tournaments/{id}`
- `/api/admin/tournaments/{id}/publish`、`/api/admin/tournaments/{id}/start`
- `/api/admin/tournaments/{id}/registrations`、`/api/admin/tournaments/{id}/registrations/{registration_id}/{action}`
- `/api/admin/tournaments/{id}/participants`
- `/api/tournaments/{id}/swiss`、`/api/tournaments/{id}/swiss/rounds`
- `/api/tournaments/{id}/matches/me`、`/api/matches/{match_id}/submissions`
- `/api/admin/tournaments/{id}/swiss/rounds`
- `/api/admin/tournaments/{id}/swiss/rounds/generate`、`/regenerate`
- `/api/admin/tournaments/{id}/swiss/rounds/{round_id}/swap`、`/publish`
- `/api/admin/matches/{match_id}/resolve`
- `/api/admin/tournaments/{id}/participants/{participant_id}/withdraw`
- `/api/tournaments/{id}/playoffs`、`/api/tournaments/{id}/playoffs/matches/me`
- `/api/playoffs/matches/{match_id}/submissions`
- `/api/admin/tournaments/{id}/playoffs`、`/api/admin/tournaments/{id}/playoffs/generate`
- `/api/admin/tournaments/{id}/playoffs/rounds/{round_id}/publish`
- `/api/admin/playoffs/matches/{match_id}/forfeit`
- `/api/admin/tournaments/{id}/end`
- `/api/tournaments/{id}/deck-submission/me`、`/api/tournaments/{id}/deck-submission`
- `/api/admin/tournaments/{id}/deck-submissions`
- `/api/admin/deck-submissions/{id}/approve`、`/return`
- `/api/admin/tournaments/{id}/reports/generate`、`/api/admin/tournaments/{id}/report`
- `/api/admin/reports/{id}/publish`
- `/api/reports`、`/api/reports/{id}`
- `/api/messages`、`/api/messages/unread-count`、`/api/messages/{id}/read`、`/api/messages/read-all`
- `/api/me/tournaments`
- `/api/admin/tournaments/{id}/messages`、`/api/admin/messages/platform`
- `/api/admin/audit-logs`

禁卡表发布后自动按 `V1.0 → V1.1 → … → V1.9 → V2.0` 递增并保留历史。公告支持更新和置顶。富文本仅允许标题、正文、加粗、列表、链接和图片等基础白名单标签。

图片上传接受有效的 JPG、PNG 和 WEBP，单文件上限 5MB、最大尺寸 6000×6000；服务会验证并重新编码图片，文件名随机生成。

QQ OAuth 需要在 `.env` 填写正式的 `QQ_OAUTH_APP_ID`、`QQ_OAUTH_APP_KEY` 和回调地址。未配置时本地账号功能正常，界面会明确显示 QQ 授权不可用。未绑定 OpenID 不会自动创建新账号，必须先验证现有本地账号后绑定。

赛事草稿不对选手公开；发布后立即开放报名，不设置报名起止时间。审核通过和恢复操作使用赛事行锁串行检查容量，避免并发超卖。存在待审核报名时禁止开赛；开赛会关闭报名、生成正式参赛名单快照并锁定容量、瑞士轮轮数、Top N 和禁卡表版本，但不会自动生成第 1 轮。

瑞士轮由管理员生成预览、调整并正式发布。第一轮随机配对，后续轮优先避免重复对手，其次尽量同胜场配对；奇数人数自动产生 BYE。双方独立提交胜/负，一致时自动确认，胜/胜或负/负进入冲突并由管理员裁定。排名固定使用胜场、OMW、败局轮次小分、直接交手和昵称稳定排序；发布下一轮才锁定上一轮赛果。管理员只能在当前轮结束且下一轮未发布时执行退赛，未发布预览会自动作废。

淘汰赛按瑞士轮最终排名取 Top N，使用固定种子签表，不支持重新抽签或交换位置。每一阶段先生成预览再发布；下一阶段发布后锁定上一阶段。选手继续使用双方独立提交胜/负，管理员可填写原因直接判负，操作写入审计记录。决赛完成后仍保持淘汰赛状态，等待管理员手动结束赛事。

管理员结束赛事后，系统永久锁定全赛事赛果并自动建立最终四强卡组提交任务。四强可上传或在审核前重新上传截图；管理员可审核通过或填写原因退回。截图审核通过后锁定。只有四强截图 4/4 审核通过，系统才允许从赛事结构化数据生成固定模板周报。周报发布后不可撤回、重新生成或修改，公开页面按发布时间倒序展示。

消息中心只记录报名审核通过/拒绝、管理员取消报名、管理员人工通知和周报发布；每轮对阵、赛果、排名及晋级变化不会产生消息。顶部显示真实未读数量，支持打开自动已读和一键全部已读。人工通知使用请求 ID 防止重复点击重复发送。我的赛事和首页当前赛事均读取真实报名、对阵和排名数据；首页仅在存在置顶公告时展示公告区域。管理员可按赛事查看关键操作审计，也可查看全平台审计记录。

## 保留的 Phase 4 开发测试数据

当前开发数据库保留一届“Phase 4 Top 8 功能测试赛”，状态为八强已发布、等待提交赛果：

- 管理员：QQ `40000000`，密码 `12345678`。
- 选手：QQ `40000001`～`40000008`，统一密码 `12345678`。
- 选手昵称：`Phase4测试选手01`～`Phase4测试选手08`。

需要在全新的开发数据库重建该数据时，可运行：

```bat
cd /d backend
.venv\Scripts\python.exe scripts\seed_phase4_test_data.py
```

脚本只允许在 `development` 环境运行，并会在同名测试赛事已存在时保持数据不变。

## 保留的 Phase 5 开发测试数据

Phase 5 继续使用上述账号，并额外保留两届已结束赛事：

- `Phase 5 卡组审核测试赛`：四强截图均未上传，适合分别登录 `40000001`～`40000004` 测试上传、复传和管理员审核。
- `Phase 5 已发布周报示例赛`：四强截图 4/4 已通过并已发布周报，适合测试 `/reports` 列表和周报详情。
- 管理员：QQ `40000000`，密码 `12345678`。
- 选手：QQ `40000001`～`40000008`，统一密码 `12345678`。

在已有 Phase 4 测试账号的开发数据库中重建 Phase 5 数据：

```bat
cd /d backend
.venv\Scripts\python.exe scripts\seed_phase5_test_data.py
```

脚本是幂等的，不会重置你已经上传或审核的测试截图。

## 保留的 Phase 6 开发测试数据

Phase 6 为选手 `40000001`（密码 `12345678`）保留置顶公告和四类消息示例，其中包含已读与未读状态、赛事通知、平台通知及周报跳转。管理员 `40000000` 可测试平台通知、单届赛事通知和操作审计。

```bat
cd /d backend
.venv\Scripts\python.exe scripts\seed_phase6_test_data.py
```

脚本只在开发环境运行且可重复执行，不会重复创建示例消息。

## 开发约束

- 业务规则以 `栗子杯网站开发文档.md` 为最高项目基线。
- 前端样式遵循 `docs/DESIGN.md`，并以 `static-preview/` 为视觉回归基线。
- 后端按 router → schema → service → repository → database 分层推进。
- 关键权限、状态锁定和并发约束必须由后端验证。
- 每个阶段通过测试并经确认后再进入下一阶段。

## V1 完成状态

Phase 0～6 的核心功能已经实现。正式上线前仍需配置 QQ OAuth、生产级数据库凭据和持久化图片存储，并使用真实部署环境完成一次人工全流程验收。

## 当前待配置事项

- QQ OAuth 正式应用凭据和最终回调域名。
- 生产环境对象存储或持久卷方案；开发阶段使用 `backend/uploads/` 本地目录。
- 生产环境必须替换 `AUTH_SECRET_KEY` 和开发数据库密码。
