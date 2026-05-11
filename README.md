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
