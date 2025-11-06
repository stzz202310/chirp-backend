## 主机与虚拟机关系
- Host(宿主机): 你自己的电脑（macOS / Windows / Linux）
- Guest(来宾机): 在宿主机中运行的虚拟机
  - 使用 VirtualBox 提供虚拟化
  - 使用 Vagrant 进行虚拟机管理和环境自动配置
> 一个 GitHub repo 对应一个 Vagrant 虚拟机环境，便于项目隔离与可复现。

---

## Vagrant 中端口映射
在 Vagrantfile 中常见设置：
```ruby
config.vm.network "forwarded_port", guest: 8000, host: 80
```
- 虚拟机(guest) 中 Django 服务跑在 8000 端口
- 宿主机(host) 通过 http://localhost:80 访问虚拟机服务
- 本质是将虚拟机端口转发到宿主机端口

---

## Django 中 Allowed Hosts
在 settings.py 中设置
```python
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
# 允许宿主机访问虚拟机指定 IP
```
作用: 限制哪些域名/IP 可以访问 Django 应用，防止未经授权的请求。