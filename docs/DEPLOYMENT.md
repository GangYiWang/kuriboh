# Ubuntu 24.04 单机 Docker Compose 部署（暂无域名）

当前先使用云服务器公网 IP 和 HTTP 部署。生产环境由同一个 Compose 项目管理：Caddy 提供前端静态文件和反向代理，FastAPI 提供 API，PostgreSQL 保存业务数据。Alembic 迁移在每次启动 API 前自动执行。以后取得域名后，只需修改环境变量即可由 Caddy 自动启用 HTTPS。

> HTTP 适合部署验证和内部验收，但登录凭证会经过未加密连接。在配置正式域名和 HTTPS 前，不建议向公众开放注册、管理员操作或真实业务数据。

## 1. 准备服务器

1. 按 [Docker 官方 Ubuntu 安装文档](https://docs.docker.com/engine/install/ubuntu/) 安装 Docker Engine 和 Compose 插件。
2. 从云服务器控制台确认服务器公网 IPv4 地址，后文用 `服务器公网IP` 表示。
3. 在云安全组和 UFW 中开放 SSH 和 TCP 80。
4. 暂时不需要开放 TCP/UDP 443；不要向公网开放 PostgreSQL 的 5432 端口。

### 允许当前用户直接使用 Docker

Docker 安装完成后，将当前 SSH 用户加入 `docker` 用户组，以后执行 `docker` 和 `docker compose` 时就不需要反复添加 `sudo`：

```bash
getent group docker >/dev/null || sudo groupadd docker
sudo usermod -aG docker "$USER"
```

退出当前 SSH 会话并重新登录，使用户组变更生效。也可以在当前会话执行下面的命令立即启用新用户组；该命令会进入一个新的 shell：

```bash
newgrp docker
```

确认当前用户属于 `docker` 组，并验证无需 `sudo` 即可运行 Docker：

```bash
id -nG
docker run --rm hello-world
docker compose version
```

> `docker` 组成员可以控制 Docker 守护进程，实际拥有接近 root 的主机权限。只应将可信的服务器运维账号加入该组，不要加入网站应用账号或其他普通用户。详见 [Docker 官方非 root 使用说明](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)。

如果之前使用 `sudo docker` 后出现 `~/.docker/config.json: permission denied`，修复当前用户 Docker 配置目录的所有权：

```bash
sudo chown -R "$USER":"$USER" "$HOME/.docker"
sudo chmod -R g+rwX "$HOME/.docker"
```

最后确认安装：

```bash
docker --version
docker compose version
```

## 2. 从旧部署清理并统一为 Kuriboh

本节只适用于服务器上曾经运行过 `lizibei-*` 或旧版 `kuriboh-*` 容器的情况。全新服务器可跳到下一节。

先查看现有容器和数据卷：

```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker volume ls
```

如果已有正式数据，必须先按本文“备份”章节备份数据库和上传文件。以下命令只清理两个 Compose 项目的容器和网络，不删除数据卷：

```bash
cd ~/Kuriboh
docker compose -p lizibei --env-file .env.production down --remove-orphans
docker compose -p kuriboh --env-file .env.production down --remove-orphans
```

不要使用 `docker rm -f $(docker ps -aq)`、`docker volume prune` 或 `docker system prune --volumes`，这些命令可能误删服务器上的其他项目或业务数据。

如确认这是全新部署，数据库、管理员账号和上传文件均不需要保留，可在人工核对 `docker volume ls` 后，单独删除已经确认属于旧部署的数据卷。不要使用通配符或批量清理命令。

新版 Compose 统一使用 `kuriboh` 项目名。重新启动后，资源名称应为：

```text
kuriboh-postgres-1
kuriboh-migrate-1
kuriboh-api-1
kuriboh-web-1
kuriboh_postgres-data
kuriboh_uploads-data
kuriboh_caddy-data
kuriboh_caddy-config
kuriboh_host-access
```

## 3. 获取代码并配置环境

```bash
git clone https://github.com/GangYiWang/kuriboh.git Kuriboh
cd Kuriboh
cp .env.production.example .env.production
chmod 600 .env.production
```

生成两个不同的随机值：

```bash
openssl rand -hex 24
openssl rand -hex 32
```

编辑 `.env.production`，将 Web 和 OAuth 部分修改为：

```env
SITE_ADDRESS=:80
HTTP_PORT=80
HTTPS_PORT=443

CORS_ORIGINS=["http://121.196.218.234"]

QQ_OAUTH_APP_ID=
QQ_OAUTH_APP_KEY=
QQ_OAUTH_REDIRECT_URI=
```

其中 `服务器公网IP` 必须替换为真实地址，不要保留中文占位符。然后配置数据库和身份密钥：

- 将第一个随机值同时写入 `POSTGRES_PASSWORD` 和 `DATABASE_URL` 的密码部分。
- 将第二个随机值写入 `AUTH_SECRET_KEY`。
- 保持 `DATABASE_URL` 中的数据库主机为 `postgres`，不能改成 `127.0.0.1`。
- 数据库密码建议使用上述十六进制随机值，以免特殊字符破坏数据库 URL。
- 暂时保持 QQ OAuth 三项为空；本地账号注册和登录不受影响。

`.env.production` 包含生产密钥，不得提交 Git，也不要发送到聊天、工单或公开日志。

## 4. 校验并启动

```bash
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production ps
```

正常情况下，Compose 只会创建以 `kuriboh-` 开头的容器和以 `kuriboh_` 开头的数据卷及网络。PostgreSQL 继续通过内部 `backend` 网络与 API 通信，同时加入仅用于宿主机端口发布的 `host-access` 桥接网络。这是为了兼容 Docker Engine 29.x 对“仅连接内部网络的容器不实际发布端口”的行为。

PostgreSQL 仍然只映射到云服务器回环地址 `127.0.0.1:5432`，供 SSH 隧道使用；不要在云安全组开放 5432。验证映射：

```bash
docker inspect kuriboh-postgres-1 \
  --format 'configured={{json .HostConfig.PortBindings}} active={{json .NetworkSettings.Ports}}'
sudo ss -lntp | grep '127.0.0.1:5432'
```

`migrate` 容器执行 `alembic upgrade head` 并正常退出后，API 才会启动。当前 `SITE_ADDRESS=:80`，Caddy 只提供 HTTP，不会申请 HTTPS 证书。

查看状态和日志：

```bash
docker compose --env-file .env.production logs --tail=100 migrate
docker compose --env-file .env.production logs --tail=100 api
docker compose --env-file .env.production logs --tail=100 web
curl -fsS http://121.196.218.234/api/health
```

浏览器访问：

```text
http://121.196.218.234
```

健康检查应返回包含 `"status":"ok"` 和 `"database":"ok"` 的 JSON。`migrate` 显示 `Exited (0)` 是正常状态，不表示部署失败。

## 5. 创建初始管理员

确认 API 健康后执行：

```bash
docker compose --env-file .env.production exec api \
  python -m app.cli create-admin --qq 你的QQ号 --nickname 你的昵称
```

按提示交互输入密码，避免将管理员密码写入终端历史。

## 6. 更新版本

更新前先完成数据库和上传文件备份：

```bash
git pull --ff-only
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d
docker compose --env-file .env.production ps
```

Compose 会先运行数据库迁移，再重建需要更新的服务。更新后检查 `http://服务器公网IP/api/health`，并人工验证登录、图片访问和后台页面。

## 7. 备份

Docker 卷用于持久化，不等于异地备份。创建仅管理员可读的备份目录：

```bash
mkdir -p backups
chmod 700 backups
```

数据库备份：

```bash
docker compose --env-file .env.production exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "backups/postgres-$(date +%F-%H%M%S).dump"
```

上传文件备份：

```bash
docker run --rm \
  -v kuriboh_uploads-data:/source:ro \
  -v "$PWD/backups:/backup" \
  alpine:3.23 \
  tar -czf "/backup/uploads-$(date +%F-%H%M%S).tar.gz" -C /source .
```

至少每天备份一次，并将备份同步到服务器之外。应定期在独立环境验证恢复流程。

## 8. 以后绑定域名并启用 HTTPS

1. 将域名 A 记录解析到服务器公网 IP。
2. 等待 DNS 生效，确认域名能够解析到该服务器。
3. 在云安全组和 UFW 中开放 TCP 443；需要 HTTP/3 时再开放 UDP 443。
4. 修改 `.env.production`：

```env
SITE_ADDRESS=你的正式域名
CORS_ORIGINS=["https://你的正式域名"]
QQ_OAUTH_REDIRECT_URI=https://你的正式域名/login/qq/callback
```

如果已经取得 QQ OAuth 正式凭据，同时填写 `QQ_OAUTH_APP_ID` 和 `QQ_OAUTH_APP_KEY`。应用配置：

```bash
docker compose --env-file .env.production up -d
docker compose --env-file .env.production logs --tail=100 web
curl -fsS https://你的正式域名/api/health
```

Caddy 会自动申请和续期 HTTPS 证书，不需要重新构建前端或后端镜像。

## 9. 常用运维命令

```bash
# 查看服务
docker compose --env-file .env.production ps

# 持续查看日志
docker compose --env-file .env.production logs -f --tail=100

# 重启 API
docker compose --env-file .env.production restart api

# 停止服务但保留数据卷
docker compose --env-file .env.production down
```

不要执行 `docker compose down -v`，该命令会删除数据库、上传文件和证书数据卷。
