# 云服务器部署指南

## 一、服务器初始化

### 1. 连接到服务器
```bash
ssh root@your_server_ip
```

### 2. 更新系统并安装依赖
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl

# CentOS/RHEL
sudo yum update -y
sudo yum install -y python3 python3-pip git curl
```

### 3. 配置Python环境
```bash
# 创建项目目录
mkdir -p /opt/wechat_auto_publish
cd /opt/wechat_auto_publish

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install requests pillow
```

## 二、上传项目文件

### 方法1：使用Git（推荐）
```bash
# 在本地创建git仓库并推送
cd c:\Users\Administrator\WorkBuddy\20260427080318\wechat_auto_publish
git init
git add .
git commit -m "Initial commit"
git remote add origin your_repo_url
git push -u origin main

# 在服务器上克隆
cd /opt/wechat_auto_publish
git clone your_repo_url .
```

### 方法2：使用SCP/SFTP上传
```bash
# 在本地电脑执行
scp -r c:\Users\Administrator\WorkBuddy\20260427080318\wechat_auto_publish\* root@your_server_ip:/opt/wechat_auto_publish/
```

### 方法3：手动创建文件
将以下文件上传到服务器：
- `main.py`
- `config.py`
- `config_env.py`
- `requirements.txt`

## 三、配置文件设置

### 1. 编辑 config.py
```python
# 微信公众平台配置
WECHAT_APPID = "你的APPID"
WECHAT_APPSECRET = "你的APPSECRET"

# 混元API配置
HUNYUAN_API_KEY = "你的API密钥"

# 代理配置（如果服务器需要）
HTTP_PROXY = None
HTTPS_PROXY = None

# 其他配置...
```

### 2. 设置文件权限
```bash
chmod 600 config.py  # 保护敏感信息
chmod +x main.py
```

## 四、测试运行

```bash
cd /opt/wechat_auto_publish
source venv/bin/activate  # 如果使用了虚拟环境
python main.py
```

检查是否成功：
- 查看输出日志
- 登录微信公众平台查看是否创建草稿

## 五、配置定时任务（Crontab）

### 1. 编辑crontab
```bash
crontab -e
```

### 2. 添加定时任务

**每天上午10点运行：**
```cron
0 10 * * * cd /opt/wechat_auto_publish && source venv/bin/activate && python main.py >> /var/log/wechat_publish.log 2>&1
```

**参数说明：**
- `0 10 * * *`：每天10:00执行
- `cd /opt/wechat_auto_publish`：切换到项目目录
- `source venv/bin/activate`：激活虚拟环境（如果用了）
- `>> /var/log/wechat_publish.log 2>&1`：记录日志

**其他时间示例：**
```cron
# 每天早上9点
0 9 * * *

# 每天下午3点
0 15 * * *

# 每周一早上10点
0 10 * * 1

# 每6小时一次
0 */6 * * *
```

### 3. 查看crontab日志
```bash
# 查看cron日志
tail -f /var/log/cron

# 查看你的脚本输出
tail -f /var/log/wechat_publish.log
```

## 六、进程守护（可选，推荐）

使用 `systemd` 或 `supervisor` 确保脚本持续运行。

### 使用 systemd

创建服务文件 `/etc/systemd/system/wechat-publish.service`：

```ini
[Unit]
Description=WeChat Auto Publish Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wechat_auto_publish
ExecStart=/opt/wechat_auto_publish/venv/bin/python /opt/wechat_auto_publish/main.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start wechat-publish
sudo systemctl enable wechat-publish  # 开机自启
sudo systemctl status wechat-publish   # 查看状态
```

## 七、微信公众号IP白名单配置

**重要：** 必须将服务器IP添加到微信公众平台白名单

1. 登录微信公众平台：https://mp.weixin.qq.com
2. 进入 **设置与开发** -> **基本配置**
3. 找到 **IP白名单**，点击 **修改**
4. 添加你的云服务器公网IP

**获取服务器公网IP：**
```bash
curl ifconfig.me
# 或
curl ip.sb
```

## 八、监控和维护

### 1. 日志查看
```bash
# 实时查看日志
tail -f /var/log/wechat_publish.log

# 查看最近100行
tail -n 100 /var/log/wechat_publish.log

# 搜索错误
grep -i "error" /var/log/wechat_publish.log
```

### 2. 磁盘空间监控
```bash
# 查看磁盘使用
df -h

# 查看图片目录大小
du -sh /opt/wechat_auto_publish/images/
```

### 3. 定期清理（可选）
```bash
# 删除30天前的图片
find /opt/wechat_auto_publish/images/ -name "*.jpg" -mtime +30 -delete

# 删除30天前的日志
find /opt/wechat_auto_publish/debug/ -name "*.txt" -mtime +30 -delete
```

## 九、故障排查

### 问题1：crontab不执行
```bash
# 检查cron服务是否运行
sudo systemctl status cron  # Ubuntu
sudo systemctl status crond # CentOS

# 查看cron日志
sudo tail -f /var/log/syslog | grep CRON  # Ubuntu
sudo tail -f /var/log/cron                # CentOS
```

### 问题2：Python路径问题
在crontab中使用绝对路径：
```cron
0 10 * * * /opt/wechat_auto_publish/venv/bin/python /opt/wechat_auto_publish/main.py
```

### 问题3：微信API报错
- 检查IP白名单
- 检查APPID和APPSECRET是否正确
- 查看 `publish_log.txt` 错误信息

## 十、安全建议

1. **不要将配置文件提交到公开仓库**
   - 在 `.gitignore` 中添加 `config.py`
   - 使用环境变量或单独的配置文件

2. **限制文件权限**
   ```bash
   chmod 600 config.py
   chown root:root config.py
   ```

3. **使用非root用户运行（可选）**
   ```bash
   sudo useradd -r -s /bin/false wechat
   sudo chown -R wechat:wechat /opt/wechat_auto_publish
   ```

4. **定期更新系统**
   ```bash
   sudo apt update && sudo apt upgrade -y  # Ubuntu
   ```

## 快速部署检查清单

- [ ] 服务器已购买并配置固定公网IP
- [ ] Python3 和 pip 已安装
- [ ] 项目文件已上传到服务器
- [ ] `config.py` 配置正确（APPID、APPSECRET、API密钥）
- [ ] 服务器IP已添加到微信公众号IP白名单
- [ ] 手动测试运行成功
- [ ] Crontab定时任务已配置
- [ ] 日志记录正常
- [ ] 监控和告警已设置（可选）

---

**下一步：** 按照上述步骤操作，如果遇到任何问题，随时告诉我！
