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
   vagrant ssh       # SSH into the VM
   vagrant halt      # Stop the VM when finished
   
2. Navigate to the project directory:
   ```bash
   cd /vagrant
   
3. Run Django commands
   ```bash
   python manage.py migrate      # Apply database migrations
   python manage.py test         # Run unit tests
   python manage.py runserver 0.0.0.0:8000
   # Start the development server, then open http://localhost:8000 in your browser

---
