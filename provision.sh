#!/usr/bin/env bash

echo 'Start!'
cd /vagrant

sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y tree
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python-is-python3
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pip


# 安装配置mysql
sudo DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.34-1_all.deb
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y libmysqlclient-dev


# 升级pip, 安装pip所需依赖
# python -m pip install --upgrade pip
pip install --upgrade pip
pip install --upgrade setuptools
pip install --ignore-installed wrapt
# 根据 requirements.txt 里的记录安装 pip package，确保所有版本之间的兼容性
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkg-config
pip install -r requirements.txt


# 设置mysql的root账户的密码为zhuzhu
# 创建名为twitter的数据库
sudo mysql -u root << EOF
	ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'zhuzhu';
	flush privileges;
	show databases;
	CREATE DATABASE IF NOT EXISTS twitter;
EOF

# 如果想直接进入/vagrant路径下
# 请输入vagrant ssh命令进入
# 手动输入
# 输入ls -a
# 输入 vi .bashrc
# 在最下面，添加cd /vagrant
echo "Python:" $(python --version)
echo "Django:" $(python -m django --version)
echo "mysqlclient:" $(python -c "import importlib.metadata as m; print(m.version('mysqlclient'))")

echo 'All Done!'
