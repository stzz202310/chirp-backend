-- 容器首次创建时自动执行（docker-entrypoint-initdb.d 机制）
-- 让 root 可以从任意 host 连接（容器互访 / 本地客户端连接均需要）
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';
FLUSH PRIVILEGES;
