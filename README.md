# Django-Twitter Backend Project

A practice project: implementing a simplified **Twitter backend** with **Django**.

---

## 🧰 Environment

| Component      | Version / Info                       | Notes                                                                          |
|----------------|--------------------------------------|--------------------------------------------------------------------------------|
| **Vagrant VM** | `bento/ubuntu-22.04`                 | [HashiCorp Vagrant Cloud](https://portal.cloud.hashicorp.com/vagrant/discover) |
| **MySQL**      | `mysql-apt-config_0.8.34-1_all.deb`  | [Download from MySQL APT Repo](https://dev.mysql.com/downloads/repo/apt/)      |
| **Python**     | `3.10.12`                            | System path: `/usr/bin/python3`                                                |
| **PyCharm**    | `Remote Python 3.10.12 (Vagrant VM)` | System Interpreter: `/usr/bin/python3`                                         |

---

## ⚙️ Setup & Run

1. Start and manage the Vagrant VM
   ```bash
   vagrant up        # Start the virtual machine
   vagrant provision # Run provision.sh to set up/configure the VM
   vagrant ssh       # SSH into the VM (ssh vagrant@127.0.0.1 -p 2222)
   vagrant halt      # Stop the VM when finished
   
2. Start MySQL and HBase interactive shells
   ```bash
   cd /vagrant/
   mysql -u root -pzhuzhu    # Start MySQL interactive shell
   
   cd /vagrant/hbase-2.4.4/
   ./bin/hbase shell         # Start HBase interactive shell
   
   telnet 127.0.0.1 11211    # Memcached
   redis-cli                 # Redis

3. Run Django commands
   ```bash
   python manage.py makemigrations
   python manage.py test         # Run unit tests
   python manage.py migrate      # Apply database migrations
   python manage.py runserver 0.0.0.0:8000
   # Start the development server, then open http://localhost in your browser
   
   python manage.py createsuperuser      # Create an admin super user (for Django admin)
   django-admin.py startproject twitter  # Create a new Django project named "twitter"
   python manage.py startapp accounts    # Create a new app called "accounts"
   python manage.py shell                # Open the Django shell (interactive Python environment)

4. Start Django server, Celery worker, HBase services, and Thrift server
   ```bash
   1. 启动 Django 开发服务器
   2. 启动 Celery Worker
   3. 启动 HBase
   4. 启动 HBase Thrift Server
      [跨语言通信框架, 用于让 Python(Django) 通过 Thrift 协议访问 Java 实现的 HBase]
   
   cd /vagrant/
   python manage.py runserver 0.0.0.0:8000
   celery -A twitter worker -l info
   
   cd /vagrant/hbase-2.4.4/
   sudo ./bin/start-hbase.sh
   sudo ./bin/hbase-daemon.sh start thrift

   Django Web UI: http://localhost:8000
   HBase Web UI: http://192.168.33.10:16010

---

## 🐳 Docker 环境

### 环境切换

本项目同时支持 Vagrant 和 Docker 两套环境，通过 `local_settings.py` 区分：

```bash
# 切换到 Docker 环境
cp twitter/local_settings_docker.py twitter/local_settings.py

# 切换回 Vagrant 环境
cp twitter/local_settings_vagrant.py twitter/local_settings.py
```

### 常用命令

```bash
make build      # 构建镜像（改了 Dockerfile 或 requirements-docker.txt 后执行）
make up         # 后台启动所有容器（mysql / redis / memcached / chirp / celery）
make down       # 停止并移除容器（数据不丢失）
make logs       # 查看所有容器实时日志（Ctrl+C 退出）
make shell      # 进入 Django 容器的 bash
make migrate    # 在容器内执行 migrate
make test       # 在容器内跑单元测试
```

### 查看单个服务日志

```bash
docker compose logs -f celery        # Celery 实时日志
docker compose logs --tail=50 chirp  # Django 最近 50 行日志
```

### 重启单个服务

```bash
docker compose restart celery   # 修改了 Celery task 代码后需执行
docker compose restart chirp    # 重启 Django（通常不需要，runserver 自动热重载）
```

### 进入数据库

```bash
# MySQL 交互式 shell
docker exec -it chirp_mysql mysql -uroot -pzhuzhu twitter

# Django shell
make shell
python manage.py shell
```

### 数据持久化说明

- 数据存储在 Docker named volume（`mysql_data`、`redis_data`），`make down` 不会清空
- **危险操作**：`docker compose down -v` 会同时删除 volume，数据不可恢复

### 代码改动是否需要重启

| 改动内容 | 需要的操作 |
|---|---|
| Python 业务代码 | 无需操作，`runserver` 自动热重载 |
| Celery task 代码 | `docker compose restart celery` |
| `Dockerfile` / `requirements-docker.txt` | `make build` |
| `docker-compose.yml` | `make down && make up` |

### 访问地址

| 服务 | 地址 |
|---|---|
| Django API | http://localhost:8000 |
| MySQL | 127.0.0.1:3306 |
| Redis | 127.0.0.1:6379 |
| Memcached | 127.0.0.1:11211 |

---
