# Docker版本升级指南（ARM边缘设备）

**目的**：将Docker 19.03.8升级到20.10.10+，以支持glibc 2.36的clone3系统调用

**适用设备**：ARM64 Linux (Sophon BM1684等)

---

## 🚀 快速升级（推荐）

### 方法1：使用Docker官方安装脚本

```bash
# 1. 备份当前Docker配置
sudo cp -r /etc/docker /etc/docker.backup.$(date +%Y%m%d)

# 2. 停止Docker服务
sudo systemctl stop docker
sudo systemctl stop docker.socket

# 3. 卸载旧版本Docker（保留镜像和容器数据）
sudo apt-get remove docker docker-engine docker.io containerd runc
# 注意：不要使用 apt-get purge，那会删除 /var/lib/docker 数据！

# 4. 使用官方脚本安装最新Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 5. 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 6. 验证版本
docker --version
# 应该显示：Docker version 20.10.x 或更高

# 7. 测试Docker正常工作
docker run hello-world
```

---

## 🔧 方法2：手动升级（适用于离线或特殊网络环境）

### Step 1: 下载Docker二进制包

```bash
# ARM64架构
wget https://download.docker.com/linux/static/stable/aarch64/docker-20.10.24.tgz

# 或从清华镜像下载（国内更快）
wget https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/aarch64/docker-20.10.24.tgz
```

### Step 2: 停止并备份

```bash
# 停止Docker
sudo systemctl stop docker

# 备份旧版本
sudo mv /usr/bin/docker /usr/bin/docker.19.03.8.backup
sudo mv /usr/bin/dockerd /usr/bin/dockerd.19.03.8.backup
```

### Step 3: 安装新版本

```bash
# 解压
tar xzvf docker-20.10.24.tgz

# 复制二进制文件
sudo cp docker/* /usr/bin/

# 重启Docker
sudo systemctl start docker

# 验证
docker --version
```

---

## ⚙️ 方法3：使用APT升级（Debian/Ubuntu）

```bash
# 1. 添加Docker官方GPG密钥
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 2. 添加Docker官方源
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 国内用户可以使用清华源
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 3. 更新并升级Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. 验证
docker --version
```

---

## ✅ 升级后验证

### 1. 检查Docker版本

```bash
docker --version
# 期望输出：Docker version 20.10.x 或更高（如 24.0.x）
```

### 2. 检查Docker服务状态

```bash
sudo systemctl status docker
# 应该显示：active (running)
```

### 3. 测试多架构支持

```bash
docker buildx version
# 如果没有buildx，安装它：
# sudo apt-get install docker-buildx-plugin
```

### 4. 验证seccomp支持

```bash
docker info | grep -i seccomp
# 应该显示 seccomp profile 相关信息
```

---

## 🔍 确认clone3支持

运行测试容器验证clone3系统调用：

```bash
# 使用bookworm镜像测试
docker run --rm -it --security-opt seccomp=unconfined python:3.10-slim bash -c "
python3 -c 'import threading; t = threading.Thread(target=lambda: print(\"Thread OK\")); t.start(); t.join(); print(\"✅ Clone3 works!\")'
"
```

**预期输出**：
```
Thread OK
✅ Clone3 works!
```

如果失败，说明Docker版本仍然太旧或seccomp配置有问题。

---

## 🐛 常见问题

### Q1: 升级后旧容器无法启动？

**A**: 重启Docker守护进程
```bash
sudo systemctl restart docker
docker ps -a  # 查看所有容器
docker start <container_id>
```

### Q2: 权限错误 "permission denied"？

**A**: 将用户加入docker组
```bash
sudo usermod -aG docker $USER
# 重新登录或执行
newgrp docker
```

### Q3: 网络连接失败？

**A**: 检查Docker网络
```bash
docker network ls
docker network prune  # 清理无用网络
```

### Q4: 镜像丢失？

**A**: 镜像应该保留在 `/var/lib/docker`
```bash
docker images  # 查看所有镜像
# 如果丢失，重新拉取
docker pull vistrat/vision:backend-v4.7-multiarch
```

---

## 🔄 回滚方案（如果升级出问题）

```bash
# 1. 停止新版本Docker
sudo systemctl stop docker

# 2. 恢复旧版本二进制
sudo mv /usr/bin/docker.19.03.8.backup /usr/bin/docker
sudo mv /usr/bin/dockerd.19.03.8.backup /usr/bin/dockerd

# 3. 恢复配置
sudo cp -r /etc/docker.backup.* /etc/docker

# 4. 重启Docker
sudo systemctl start docker

# 5. 验证
docker --version
```

---

## 📋 升级前检查清单

- [ ] 备份 `/etc/docker` 配置目录
- [ ] 记录当前Docker版本 `docker --version`
- [ ] 确认所有容器已停止 `docker ps`
- [ ] 确认网络畅通（可访问Docker Hub或国内镜像）
- [ ] 准备回滚方案

---

## 📊 升级完成后的配置验证

### docker-compose.yml 配置（已优化）

```yaml
backend:
  image: vistrat/vision:backend-v4.7-multiarch
  security_opt:
    - seccomp:unconfined  # ✅ 保留此配置作为双保险
  ulimits:
    nproc: 65535
    nofile:
      soft: 65535
      hard: 65535
```

**说明**：
- Docker 20.10.10+ 原生支持clone3，但保留 `seccomp:unconfined` 作为双保险
- `ulimits` 确保有足够的进程和文件描述符配额

---

## ✅ 最终验证

在ARM边缘设备上部署后台服务并验证：

```bash
# 1. 拉取最新镜像
docker pull vistrat/vision:backend-v4.7-multiarch

# 2. 更新docker-compose.yml中的镜像标签
# 将 image: vistrat/vision:backend-v3.6-multiarch
# 改为 image: vistrat/vision:backend-v4.7-multiarch

# 3. 重启服务
cd /path/to/project
docker-compose down
docker-compose up -d

# 4. 查看日志，确认无 "can't start new thread" 错误
docker-compose logs -f backend | grep -E "can't start new thread|ERROR|✅"
```

**成功标志**：
- ✅ 系统正常启动
- ✅ 用户登录成功
- ✅ 视频流分析正常
- ✅ 无 "can't start new thread" 错误

---

## 🎯 为什么需要升级Docker？

### 技术原因

1. **glibc 2.34+使用clone3**
   - Python 3.10 + Debian bookworm = glibc 2.36
   - glibc 2.34+默认使用clone3()系统调用创建线程

2. **Docker seccomp策略**
   - Docker 19.03.8: seccomp默认阻止clone3，返回EPERM
   - Docker 20.10.10+: seccomp支持clone3，返回成功或ENOSYS

3. **glibc行为**
   - 看到EPERM: 认为是致命错误，不降级到clone()
   - 看到ENOSYS: 自动降级到传统clone()

### 问题链

```
glibc 2.36 尝试 clone3()
    ↓
Docker 19.03.8 seccomp 阻止 → EPERM
    ↓
glibc 认为致命错误 → 不降级
    ↓
所有线程创建失败 → "can't start new thread"
```

### 解决方案对比

| 方案 | 效果 | 成本 |
|------|------|------|
| 降级到bullseye (glibc 2.31) | ❌ QEMU构建崩溃 | 低 |
| 升级Docker到20.10.10+ | ✅ 完美解决 | 低 |
| 使用seccomp:unconfined | ⚠️ 部分缓解 | 低 |

---

**文档创建时间**: 2025-10-27
**适用场景**: ARM64 Linux + Docker 19.x升级
**推荐方法**: 官方安装脚本（方法1）
