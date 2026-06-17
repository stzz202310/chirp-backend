# Chirp 项目部署笔记
## Docker 容器化 + EC2 生产部署

---

## 一、整体架构

```
浏览器
  │
  ▼
Nginx (EC2 宿主机, port 80)
  ├── /api/*          → 反向代理 → Gunicorn:8000 (Docker 容器)
  ├── /admin/*        → 反向代理 → Gunicorn:8000 (Docker 容器)
  ├── /django-static/ → Django collectstatic 产物 (宿主机目录)
  └── /               → React build 静态文件 (宿主机目录)

Docker 容器网络 (chirp-backend-main_default)
  ├── chirp_web       (Django + Gunicorn, port 8000)
  ├── chirp_celery    (Celery worker, 消费 default + newsfeeds 队列)
  ├── chirp_mysql     (MySQL 8.0, port 3306)
  ├── chirp_redis     (Redis 7, port 6379)
  └── chirp_memcached (Memcached 1.6, port 11211)

AWS S3
  └── django-twitter-zhuzhu (存储头像 + 推文图片)
```

---

## 二、Nginx

Nginx 是一个**反向代理**——代理在服务器这边，替服务器接收请求，再根据路径决定转给谁处理。

浏览器不知道 Gunicorn 的存在，它只知道 Nginx。

### 实际请求流程举例

**请求 1：`GET http://13.57.32.157/`（打开首页）**
```
浏览器 → Nginx
Nginx 看：路径是 /
匹配 location / → 直接从 /home/ubuntu/chirp/frontend/build 读 index.html
Nginx 返回 index.html → 浏览器
（Gunicorn/Django 完全没有参与）
```

**请求 2：`GET http://13.57.32.157/static/js/main.3c356ec7.js`（加载 React JS bundle）**
```
浏览器 → Nginx
Nginx 看：路径是 /static/js/...
匹配 location / → try_files 在 /frontend/build 里找到文件
Nginx 直接返回 JS 文件 → 浏览器
（Gunicorn/Django 完全没有参与）
```

**请求 3：`POST http://13.57.32.157/api/accounts/login/`（用户点登录按钮）**
```
React 里的 loginAPI() 调用 axios.post('/api/accounts/login/', {...})
→ 浏览器发出这个 HTTP 请求 → Nginx
Nginx 看：路径是 /api/ 开头
匹配 location /api/ → 转发给 http://127.0.0.1:8000（Gunicorn）
Django 验证用户名密码 → 返回 JSON → Nginx → 浏览器
```

**请求 4：`GET http://13.57.32.157/profile`（用户点进个人页，React Router 路由）**
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

### 关键区分：前端路由 vs API 请求

| | 路径示例 | 谁发的 | Nginx 怎么处理 |
|--|---------|--------|---------------|
| 前端路由 | `/login` `/profile` `/createTweet` | 用户在浏览器地址栏输入/点击链接 | 回退到 index.html，React Router 处理 |
| API 请求 | `/api/accounts/login/` `/api/tweets/` | React 组件里的 axios 代码 | 转发给 Gunicorn |

`/login`、`/createTweet` 这些路径只告诉 React「渲染哪个组件」，和后端无关。
后端 API 路径（`/api/...`）定义在 `userAPI.js`、`tweetAPI.js` 里，是 axios 单独发的请求。

### 为什么安全组不开 8000 端口？

技术上可以让 Nginx 监听 8000 再转给 Gunicorn，但问题在于**安全组开了 8000，浏览器就能绕过 Nginx 直接打到 Gunicorn**：

```
安全组开了 8000：
  浏览器 → 直接打 http://13.57.32.157:8000/api/  ← 绕过 Nginx，Gunicorn 裸奔在公网
  浏览器 → http://13.57.32.157:80 → Nginx → Gunicorn  ← 正常路径

安全组只开 80：
  浏览器只能打 80，Nginx 是唯一入口，8000 从外面根本访问不到
```

Gunicorn 是纯 Python 进程，直接暴露在公网没有任何防护——没有限流、没有静态文件处理、没有 SSL。所以让 Gunicorn 只在 Docker 内部网络里跑，外面统一走 Nginx。

Nginx 做了很多 Gunicorn 不擅长的事：
- 直接托管静态文件（CSS/JS），速度极快，不占 Django 进程
- SSL 终结（HTTPS 解密在 Nginx 这层做，Django 不用管）
- 限流、压缩、缓存
- **高并发连接处理**（见下方）

### Nginx 的高并发能力

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

### 一个 Nginx 可以对应多个 Gunicorn

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

我现在的项目只有一个 Gunicorn，但 Nginx 已经在根据**路径**分发了：

```
/api/*    → Gunicorn 8000（Django 处理）
/admin/*  → Gunicorn 8000（同一个）
/         → 直接返回静态文件（不走 Gunicorn）
```

不管后面跑几个服务、什么语言，外面统一走 80/443，Nginx 在里面做路由。

---

## 三、Docker 容器化

### 关键概念

- **容器服务名 = 容器内的主机名**：同一个 compose 网络里，容器之间通过服务名互访（如 `mysql`、`redis`、`memcached`），不用 `127.0.0.1`
- **healthcheck**：让依赖服务（Django）等 mysql/redis 真正就绪后再启动，避免启动时序问题
- **named volume**：`mysql_data`、`redis_data` 保证数据在容器重启后持久化

### Dockerfile 要点

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

### docker-compose.yml（开发版 vs 生产版的区别）

| 配置项 | 开发版 | 生产版 |
|--------|--------|--------|
| Django 启动命令 | `runserver 0.0.0.0:8000` | `gunicorn -c gunicorn.conf.py twitter.wsgi:application` |
| 代码 volume | `- .:/app`（本地改动即时生效） | 不挂载，用镜像里的代码（改了代码要重新 `docker compose up --build`） |
| collectstatic | 不需要 | 启动时自动执行 `python manage.py collectstatic` |
| staticfiles volume | 无 | `staticfiles:/app/staticfiles`（供 Nginx 读取） |

### WSGI 是什么？

WSGI（Web Server Gateway Interface）是一个**协议/接口规范**，定义了 Web 服务器和 Python Web 应用之间怎么通信：

```
Nginx ──► Gunicorn ──► Django
（Web服务器） （WSGI Server） （WSGI Application）
```

- **Gunicorn** 是 WSGI Server——它懂 HTTP，能接收网络请求，然后按 WSGI 规范调用 Django
- **Django** 是 WSGI Application——它不懂网络，只懂「收到一个请求对象，返回一个响应对象」
- **WSGI** 就是 Gunicorn 和 Django 之间的「合同」，规定了请求和响应的格式
- **`twitter/wsgi.py`**：Django 暴露给 Gunicorn 的入口文件，里面的 `application` 对象就是那个 WSGI Application

### gunicorn.conf.py

- `127.0.0.1:8000`：只接受**来自本机**的连接，其他机器/容器访问不到
- `0.0.0.0:8000`：接受**来自任何地址**的连接，包括容器网络内的其他容器

我的架构里 Nginx 装在宿主机，Gunicorn 跑在 Docker 容器里。Nginx 通过 `127.0.0.1:8000` 访问 Gunicorn，这个请求从宿主机进入容器，**不是**容器内部的本地请求，所以必须用 `0.0.0.0`，用 `127.0.0.1` 的话 Nginx 的请求会被 Gunicorn 拒掉。

### 为什么生产用 Gunicorn 不用 runserver？

- `runserver` 是单线程开发服务器，性能差、不安全，官方明确不推荐生产使用
- `gunicorn` 是生产级 WSGI 服务器，多 worker 并发处理请求

---

## 四、静态文件分类与路径设计

### 三种静态文件分别在哪里

| 文件类型 | 具体内容 | 存哪里 | 谁托管 |
|---------|---------|--------|--------|
| Django Admin CSS/JS | `/admin/` 后台的样式和脚本 | EC2 `/app/staticfiles` | Nginx `/django-static/` |
| 用户头像 / 推文图片 | 用户上传的媒体文件 | AWS S3 | S3 直接返回 |
| 前端 React CSS/JS | React build 产物 | EC2 `/chirp/frontend/build` | Nginx `/` |

`python manage.py collectstatic` 做的事：把所有 Django app 里散落的 static 文件收集到 `STATIC_ROOT`，Nginx 从这里直接返回，不经过 Django 进程。

### 为什么 Django static 用 `/django-static/` 而不是 `/static/`？

前端 React build 产物的路径也是 `/static/`（`build/static/css/`、`build/static/js/`）。

如果 Nginx 把 `/static/` 配给 Django staticfiles，前端的 CSS/JS 就会被错误拦截，页面空白报错：
```
failed to load a stylesheet from a URL
```

**解决方案**：Django 静态文件改用 `/django-static/` 路径，前端的 `/static/` 交给 `location /` 的 `try_files` 自然处理，两者互不干扰。

---

## 五、EC2 实例配置

### 安全组规则

| 端口 | 来源 | 用途 |
|------|------|------|
| 22 (SSH) | My IP only | SSH 连服务器，不对公网开放 |
| 80 (HTTP) | Anywhere | 对外提供网站访问 |

### 两个 IP 的区别

- 公网 IP：互联网任何人可以访问，浏览器里用这个
- 内网 IP：AWS VPC 内部地址，外网访问不到

两个都加进 `ALLOWED_HOSTS` 是保险做法。

---

## 六、TODO（下一步）

- [ ] GitHub Actions CI/CD：push → 自动部署到 EC2
- [ ] README：架构图、技术栈说明、live URL
- [ ] 域名 + HTTPS：买域名 → DNS → Certbot Let's Encrypt
- [ ] EC2 重启自动拉起容器：配置 systemd service
- [ ] AWS IAM Access Key 轮换（当前 key 已暴露）
- [ ] Vercel 前端分离部署（可选，练 CORS）
