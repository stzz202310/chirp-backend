# Chirp 项目部署笔记
## Docker 容器化 + EC2 生产部署

---

## 目录

- [一、整体架构](#一整体架构)
- [二、Nginx](#二nginx)
  - [2.1 实际请求流程举例](#21-实际请求流程举例)
  - [2.2 前端路由 vs API 请求](#22-前端路由-vs-api-请求)
  - [2.3 为什么安全组不开 8000 端口？](#23-为什么安全组不开-8000-端口)
  - [2.4 Nginx 的高并发能力](#24-nginx-的高并发能力)
  - [2.5 一个 Nginx 可以对应多个 Gunicorn](#25-一个-nginx-可以对应多个-gunicorn)
- [三、Docker 容器化](#三docker-容器化)
  - [3.0 关键概念](#30-关键概念)
  - [3.1 Dockerfile 要点](#31-dockerfile-要点)
  - [3.2 docker-compose.yml（开发版 vs 生产版的区别）](#32-docker-composeyml开发版-vs-生产版的区别)
  - [3.3 WSGI 是什么？](#33-wsgi-是什么)
  - [3.4 gunicorn.conf.py](#34-gunicornconfpy)
  - [3.5 为什么生产用 Gunicorn 不用 runserver？](#35-为什么生产用-gunicorn-不用-runserver)
- [四、静态文件分类与路径设计](#四静态文件分类与路径设计)
  - [4.1 三种静态文件分别在哪里](#41-三种静态文件分别在哪里)
  - [4.2 为什么 Django static 用 `/django-static/` 而不是 `/static/`？](#42-为什么-django-static-用-django-static-而不是-static)
  - [4.3 Debug：Django Admin 403 / CSS 加载失败（named volume → bind mount）](#43-debugdjango-admin-403--css-加载失败named-volume--bind-mount)
- [五、域名 + HTTPS](#五域名--https)
  - [5.1 步骤](#51-步骤)
  - [5.2 前端开发环境的跨域：craco proxy](#52-前端开发环境的跨域craco-proxy)
  - [5.3 Elastic IP：解决 EC2 重启后 IP 变化的问题](#53-elastic-ip解决-ec2-重启后-ip-变化的问题)

---

## 一、整体架构

```
浏览器
  │
  ▼
Nginx (EC2 宿主机, port 80/443)
  ├── /api/*          → 反向代理 → Gunicorn:8000 (Docker 容器)
  ├── /admin/*        → 反向代理 → Gunicorn:8000 (Docker 容器)
  ├── /django-static/ → Django collectstatic 产物 (宿主机目录)
  └── /               → React build 静态文件 (宿主机目录)

Docker 容器网络 (chirp-backend_default)
  ├── chirp_web       (Django + Gunicorn, port 8000)
  ├── chirp_celery    (Celery worker, 消费 default + newsfeeds 队列)
  ├── chirp_mysql     (MySQL 8.0, port 3306)
  ├── chirp_redis     (Redis 7, port 6379)
  └── chirp_memcached (Memcached 1.6, port 11211)

AWS S3
  └── django-twitter-zhuzhu (存储头像 + 推文图片，IAM Role 访问)
```

---

## 二、Nginx

Nginx 是一个**反向代理**——代理在服务器这边，替服务器接收请求，再根据路径决定转给谁处理。

浏览器不知道 Gunicorn 的存在，它只知道 Nginx。

### 2.1 实际请求流程举例

**请求 1：`GET https://chirp-app.dev/`（打开首页）**
```
浏览器 → Nginx
Nginx 看：路径是 /
匹配 location / → 直接从 /home/ubuntu/chirp/frontend/build 读 index.html
Nginx 返回 index.html → 浏览器
（Gunicorn/Django 完全没有参与）
```

**请求 2：`GET https://chirp-app.dev/static/js/main.3c356ec7.js`（加载 React JS bundle）**
```
浏览器 → Nginx
Nginx 看：路径是 /static/js/...
匹配 location / → try_files 在 /frontend/build 里找到文件
Nginx 直接返回 JS 文件 → 浏览器
（Gunicorn/Django 完全没有参与）
```

**请求 3：`POST https://chirp-app.dev/api/accounts/login/`（用户点登录按钮）**
```
React 里的 loginAPI() 调用 axios.post('/api/accounts/login/', {...})
→ 浏览器发出这个 HTTP 请求 → Nginx
Nginx 看：路径是 /api/ 开头
匹配 location /api/ → 转发给 http://127.0.0.1:8000（Gunicorn）
Django 验证用户名密码 → 返回 JSON → Nginx → 浏览器
```

**请求 4：`GET https://chirp-app.dev/profile`（用户点进个人页，React Router 路由）**
```
浏览器 → Nginx
Nginx 看：路径是 /profile
匹配 location /
try_files 先找 /build/profile 文件 → 不存在
try_files 再找 /build/profile/ 目录 → 不存在
try_files 最后回退到 /index.html → 返回给浏览器
浏览器拿到 index.html，React 启动，React Router 看到 /profile，渲染 Profile 组件
React 再发 /api/ 请求拿数据
```

### 2.2 前端路由 vs API 请求

| | 路径示例 | 谁发的 | Nginx 怎么处理 |
|--|---------|--------|---------------|
| 前端路由 | `/login` `/profile` `/createTweet` | 用户在浏览器地址栏输入/点击链接 | 回退到 index.html，React Router 处理 |
| API 请求 | `/api/accounts/login/` `/api/tweets/` | React 组件里的 axios 代码 | 转发给 Gunicorn |

`/login`、`/createTweet` 这些路径只告诉 React「渲染哪个组件」，和后端无关。
后端 API 路径（`/api/...`）定义在 `userAPI.js`、`tweetAPI.js` 里，是 axios 单独发的请求。

### 2.3 为什么安全组不开 8000 端口？

技术上可以让 Nginx 监听 8000 再转给 Gunicorn，但问题在于**安全组开了 8000，浏览器就能绕过 Nginx 直接打到 Gunicorn**：

```
安全组开了 8000：
  浏览器 → 直接打 http://<IP>:8000/api/  ← 绕过 Nginx，Gunicorn 裸奔在公网
  浏览器 → http://<IP>:80 → Nginx → Gunicorn  ← 正常路径

安全组只开 80/443：
  浏览器只能打 80/443，Nginx 是唯一入口，8000 从外面根本访问不到
```

Gunicorn 是纯 Python 进程，直接暴露在公网没有任何防护——没有限流、没有静态文件处理、没有 SSL。所以让 Gunicorn 只在 Docker 内部网络里跑，外面统一走 Nginx。

Nginx 做了很多 Gunicorn 不擅长的事：
- 直接托管静态文件（CSS/JS），速度极快，不占 Django 进程
- SSL 终结（HTTPS 解密在 Nginx 这层做，Django 不用管）
- 限流、压缩、缓存
- **高并发连接处理**（见下方）

### 2.4 Nginx 的高并发能力

**没有 Nginx，直接用 Gunicorn：**

```
Request 1 ──► Gunicorn Worker 1（忙）
Request 2 ──► 等待... 直到 Worker 1 处理完才能进来
Request 3 ──► 继续等待...
```

Gunicorn worker 数量固定（2个），超过 2 个并发请求就得排队等 worker 空出来。

**有 Nginx：**

```
Request 1  ┐
Request 2  ├──► Nginx（先全部接收，存在内存缓冲区）──► 分发给空闲的 Gunicorn Worker
Request 3  ┘
...
1000个请求  ──► Nginx 照单全收，慢慢喂给 Gunicorn
```

Nginx 是用 C 写的，采用**事件驱动、异步非阻塞**模型，接收连接几乎不消耗资源，同时维持几万个连接完全没问题。它的角色是「蓄水池」——先把所有请求接住，再按 Gunicorn 的处理速度有序地喂进去，不会让 Gunicorn 直接被淹没。

**处理慢客户端：** 手机网络很慢，上传图片要 10 秒。没有 Nginx 的话，这 10 秒内，Gunicorn 的一个 worker 就被占着什么都干不了。有 Nginx 的话，Nginx 先把完整请求接收完，再一次性交给 Gunicorn，worker 只需要处理几毫秒。

### 2.5 一个 Nginx 可以对应多个 Gunicorn

Nginx 最经典的用法之一：一台服务器上跑多个项目（比如 twitter、直播、购物），每个项目一个 Gunicorn，Nginx 根据**域名**分发：

```nginx
# 项目 A
server {
    server_name api.chirp.com;
    location / { proxy_pass http://127.0.0.1:8000; }  # Django
}

# 项目 B
server {
    server_name admin.chirp.com;
    location / { proxy_pass http://127.0.0.1:8001; }  # 另一个 Django 项目
}

# 项目 C（Go 服务）
server {
    server_name go.chirp.com;
    location / { proxy_pass http://127.0.0.1:9000; }
}
```

本项目只有一个 Gunicorn，但 Nginx 已经在根据**路径**分发了：

```
/api/*    → Gunicorn 8000（Django 处理）
/admin/*  → Gunicorn 8000（同一个）
/         → 直接返回静态文件（不走 Gunicorn）
```

不管后面跑几个服务、什么语言，外面统一走 80/443，Nginx 在里面做路由。

---

## 三、Docker 容器化

### 3.0 关键概念

- **容器服务名 = 容器内的主机名**：同一个 compose 网络里，容器之间通过服务名互访（如 `mysql`、`redis`、`memcached`），不用 `127.0.0.1`
- **healthcheck**：让依赖服务（Django）等 mysql/redis 真正就绪后再启动，避免启动时序问题
- **named volume**：`mysql_data`、`redis_data` 保证数据在容器重启后持久化

### 3.1 Dockerfile 要点

```dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1   # 不生成 .pyc 文件
ENV PYTHONUNBUFFERED=1          # 日志实时输出，不缓冲

# 先只拷贝 requirements，利用 Docker 层缓存
# 只要 requirements 没变，pip install 这层会被缓存，重新 build 更快
COPY requirements-docker.txt .
RUN pip install -r requirements-docker.txt

COPY . .   # 再拷贝其余代码
```

### 3.2 docker-compose.yml（开发版 vs 生产版的区别）

| 配置项 | 开发版 | 生产版 |
|--------|--------|--------|
| Django 启动命令 | `runserver 0.0.0.0:8000` | `gunicorn -c gunicorn.conf.py twitter.wsgi:application` |
| 代码 volume | `- .:/app`（本地改动即时生效） | 不挂载，用镜像里的代码（改了代码要重新 `docker compose up --build`） |
| collectstatic | 不需要 | 启动时自动执行 `python manage.py collectstatic` |
| staticfiles volume | 无 | `./staticfiles:/app/staticfiles`（bind mount，供 Nginx 直接读取） |

### 3.3 WSGI 是什么？

WSGI（Web Server Gateway Interface）是一个**协议/接口规范**，定义了 Web 服务器和 Python Web 应用之间怎么通信：

```
Nginx ──► Gunicorn ──► Django
（Web服务器） （WSGI Server） （WSGI Application）
```

- **Gunicorn** 是 WSGI Server——它懂 HTTP，能接收网络请求，然后按 WSGI 规范调用 Django
- **Django** 是 WSGI Application——它不懂网络，只懂「收到一个请求对象，返回一个响应对象」
- **WSGI** 就是 Gunicorn 和 Django 之间的「合同」，规定了请求和响应的格式
- **`twitter/wsgi.py`**：Django 暴露给 Gunicorn 的入口文件，里面的 `application` 对象就是那个 WSGI Application

### 3.4 gunicorn.conf.py

- `127.0.0.1:8000`：只接受**来自本机**的连接，其他机器/容器访问不到
- `0.0.0.0:8000`：接受**来自任何地址**的连接，包括容器网络内的其他容器

本项目架构里 Nginx 装在宿主机，Gunicorn 跑在 Docker 容器里。Nginx 通过 `127.0.0.1:8000` 访问 Gunicorn，这个请求从宿主机进入容器，**不是**容器内部的本地请求，所以必须用 `0.0.0.0`，用 `127.0.0.1` 的话 Nginx 的请求会被 Gunicorn 拒掉。

### 3.5 为什么生产用 Gunicorn 不用 runserver？

- `runserver` 是单线程开发服务器，性能差、不安全，官方明确不推荐生产使用
- `gunicorn` 是生产级 WSGI 服务器，多 worker 并发处理请求

---

## 四、静态文件分类与路径设计

### 4.1 三种静态文件分别在哪里

| 文件类型 | 具体内容 | 存哪里 | 谁托管 |
|---------|---------|--------|--------|
| Django Admin CSS/JS | `/admin/` 后台的样式和脚本 | EC2 `./staticfiles/`（bind mount） | Nginx `/django-static/` |
| 用户头像 / 推文图片 | 用户上传的媒体文件 | AWS S3 | S3 直接返回 |
| 前端 React CSS/JS | React build 产物 | EC2 `/chirp/frontend/build` | Nginx `/` |

`python manage.py collectstatic` 做的事：把所有 Django app 里散落的 static 文件收集到 `STATIC_ROOT`，Nginx 从这里直接返回，不经过 Django 进程。

### 4.2 为什么 Django static 用 `/django-static/` 而不是 `/static/`？

前端 React build 产物的路径也是 `/static/`（`build/static/css/`、`build/static/js/`）。如果 Nginx 把 `/static/` 配给 Django staticfiles，前端的 CSS/JS 就会被错误拦截，页面空白报错。

**解决方案**：Django 静态文件改用 `/django-static/` 路径，前端的 `/static/` 交给 `location /` 的 `try_files` 自然处理，两者互不干扰。

### 4.3 Debug：Django Admin 403 / CSS 加载失败（named volume → bind mount）

**表象**：`/admin/`、DRF 浏览式页面返回 403；CSS/JS 全部加载失败。

**根因链路**：
```
第一层：Nginx alias 指向 Docker named volume 内部路径
        (/var/lib/docker/volumes/.../_data/)
        /var/lib/docker 权限 750，Nginx (www-data) 无法访问 → 403
  ↓
第二层：改用 bind mount 后重新 docker compose up --build，
        手动建的 local_settings.py 软链接不在 git 里，build 后消失
        → Django 退回默认配置，数据库连接 / ALLOWED_HOSTS 全部失效
  ↓
根本解决：ln -sf 写进 Dockerfile，每次 build 自动重建，不依赖手动操作
```

**Bind mount vs Named volume**：

| | Bind mount | Named volume |
|---|---|---|
| 写法 | `- ./staticfiles:/app/staticfiles` | `- staticfiles:/app/staticfiles` |
| 宿主机路径 | 你指定的普通目录 | Docker 自管 `/var/lib/docker/volumes/...` |
| 权限 | 标准 Linux 权限，外部进程可访问 | Docker 锁死，外部进程无法访问 |
| 适合场景 | 宿主机需要直接读写（如 Nginx 读 static） | 容器间共享，无需宿主机介入（如 mysql_data） |

`staticfiles` 需要被 Nginx（宿主机进程）直接读取，天生是 bind mount 的场景；误用 named volume 导致 Nginx 被 Docker 权限设计天然拒绝。

---

## 五、域名 + HTTPS

### 5.1 步骤

```
买域名（Namecheap） → DNS A Record 指向 EC2 IP → Nginx server_name 改成域名 → Certbot 申请证书 → HTTPS 跑通
```

1. **买域名**：Namecheap 搜索可用域名，`chirp-app.dev`（注意 `.dev` 域名强制要求 HTTPS，浏览器直接拒绝 HTTP）
2. **配 DNS**：Namecheap → Advanced DNS → 加 A Record，`@` 指向 EC2 公网 IP；再加一条 CNAME，`www` 指向主域名（不然 `www.xxx` 子域名查不到 DNS，Certbot 会报 NXDOMAIN）
3. **改 Nginx `server_name`**：从 IP 改成域名
   ```nginx
   server_name chirp-app.dev www.chirp-app.dev;
   ```
4. **装 Certbot 并申请证书**：
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d chirp-app.dev -d www.chirp-app.dev
   ```
   Certbot 会自动改 Nginx 配置加上 443 监听和证书路径，并设置好自动续期（到期前自动更新，不用手动操作）
5. **安全组开 443 端口**：Type HTTPS，Port 443，Source Anywhere（80 之外必须额外开，不然证书申请成功了浏览器还是转圈圈连不上）
6. **更新 Django 配置**：`ALLOWED_HOSTS` 加域名，`CSRF_TRUSTED_ORIGINS` 从 `http://` 改成 `https://`

### 5.2 前端开发环境的跨域：craco proxy

本地开发时前端跑在 `:3000`，后端跑在 `:8000`，是跨域的。`craco.config.js` 里配了开发服务器代理解决这个问题：

```javascript
module.exports = {
  devServer: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
};
```

浏览器请求 `/api/*` → webpack-dev-server（Node 服务器）→ 转发到 `http://localhost:8000/api/*`。
请求由 Node 服务器代发，不受浏览器同源策略约束，绕过了开发环境下的 CORS 问题。

**这个 proxy 只在 `npm start` 开发模式下生效。** `npm run build` 出来的生产静态文件没有这个代理逻辑——这也是为什么生产环境选择前后端同源部署（Nginx 同时托管前端 build 和反代后端 API），而不是依赖 CORS：现有前端代码本来就是按「同源」假设写的（相对路径 `/api/...`），同源部署正好复用这个假设，不用额外装 `django-cors-headers` 改前端跨域逻辑。

### 5.3 Elastic IP：解决 EC2 重启后 IP 变化的问题

**问题链条：**

```
EC2 重启 → 公网 IP 变化 → DNS A Record 需要手动更新 → 本地 DNS 缓存导致连接失败
  ↓
申请 Elastic IP → 绑定到实例 → 更新 A Record（最后一次）
  ↓
以后 EC2 Stop/Start/Reboot，公网 IP 永远不变，不再需要更新任何配置
```

**遇到的具体现象：** DNS A Record 已经更新成新 IP，`nslookup` 也能查到正确结果，但 `ssh chirp`（用域名连接）却连不上，卡在 "Connecting to..." 不动；直接用新 IP 连接反而成功。

**根因分析：**

```
之前用旧 IP 访问过 chirp-app.dev（部署/测试阶段）
  → Mac 系统层面的 DNS 解析器把 "chirp-app.dev → 旧IP" 这条记录缓存了下来
  → EC2 重启后 IP 变了，Namecheap 上的 A Record 也更新成新 IP 了
  → 但 Mac 本地的缓存还在用旧记录，没有过期/刷新
  → ssh chirp 时，系统优先查本地缓存，查到旧 IP，连接旧 IP（已经不存在/没人监听），结果卡死
  → nslookup 命令走的是另一条路径（直接发 DNS query 给指定服务器，不查本地缓存），
    所以它能看到最新结果，造成"nslookup 说对、ssh 却连不上"的错位现象
```

这是 DNS 系统设计的正常行为——DNS 记录有 TTL（Time To Live），缓存在过期前会一直被使用，是为了减少重复查询、加快访问速度。但这也意味着记录更新后，旧缓存不会立刻消失，要等 TTL 到期或手动清缓存：

```bash
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

**根本解决方案：Elastic IP。** 一旦绑定固定公网 IP，EC2 重启就不会再触发"改 DNS → 等缓存过期/手动刷新"这一整套连锁问题，域名永远指向同一个 IP，不会再有这种缓存错位的情况。

