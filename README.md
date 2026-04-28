# 微信公众号每日短篇小说自动发布系统

> 每天早上 07:50 自动运行 → 生成小说文案 + AI配图 → 08:00 前准时发布到微信公众号

---

## 一、快速开始（3步上线）

### 第1步：安装依赖

```powershell
cd c:\Users\Administrator\WorkBuddy\20260427080318\wechat_auto_publish
pip install requests
```

### 第2步：填写配置（`config.py`）

打开 `config.py`，填写以下4个关键值：

```python
WECHAT_APP_ID     = "wx开头的18位字符"   # 公众号后台 → 设置 → 基本配置
WECHAT_APP_SECRET = "32位字符串"          # 同上
HUNYUAN_SECRET_ID  = "AKIDxxxxxxxx"       # 腾讯云控制台 → 访问管理 → API密钥
HUNYUAN_SECRET_KEY = "xxxxxxxx"           # 同上
```

### 第3步：激活定时任务

在 WorkBuddy 的**自动化**面板中，找到「微信公众号每日小说自动发布」，点击**启用**即可。

---

## 二、每日风格轮排

| 星期 | 风格 | 内容特色 |
|------|------|---------|
| 周一 | 都市情感 | 爱情/职场/家庭，细腻温情 |
| 周二 | 悬疑推理 | 谜题/反转/真相，烧脑刺激 |
| 周三 | 古风仙侠 | 穿越/修仙/宫斗，古雅优美 |
| 周四 | 治愈暖心 | 温情/成长/善意，抚慰心灵 |
| 周五 | 今日特辑 | 随机风格，创意先行 |
| 周六 | 治愈暖心 | 同周四 |
| 周日 | 今日特辑 | 同周五 |

---

## 三、执行流程

```
07:50 定时触发
   ↓
① 识别今日星期 → 匹配风格配置
   ↓
② 调用腾讯混元 API → 生成 800-1200 字小说（含标题）
   ↓
③ 调用混元文生图 API → 生成 1024×1024 配图
   ↓
④ 图片备份到 images/ 目录
   ↓
⑤ 上传图片到微信永久素材库
   ↓
⑥ 创建微信图文草稿
   ↓
⑦ 调用微信群发接口发布
   ↓
08:00 前完成，订阅者收到推送
```

---

## 四、文件目录说明

```
wechat_auto_publish/
├── config.py          ← ⭐ 配置文件，填写 API Key
├── main.py            ← 主执行脚本
├── README.md          ← 本说明文档
├── publish_log.txt    ← 运行日志（自动生成）
└── images/            ← 每日配图备份（自动生成）
    └── 20260428_cover.jpg
```

---

## 五、手动测试

不想等定时任务，可以立即手动运行验证配置是否正确：

```powershell
cd c:\Users\Administrator\WorkBuddy\20260427080318\wechat_auto_publish
python main.py
```

观察终端输出和 `publish_log.txt`，看到 `✅ 发布完成` 即表示成功。

---

## 六、常见问题

### Q: 提示 `access_token 获取失败`
- 检查 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET` 是否正确
- 确认公众号 IP 白名单已添加本机 IP（公众号后台 → 基本配置 → IP白名单）

### Q: 提示 `上传图片失败 / 素材数量已达上限`
- 订阅号永久素材上限为 5000 个，定期清理旧素材

### Q: 混元 API 报错 `AuthFailure`
- 检查 `HUNYUAN_SECRET_ID` 和 `HUNYUAN_SECRET_KEY`
- 在腾讯云控制台确认已开通「混元大模型」和「混元文生图」服务

### Q: 文章发布后显示「发布中」而非立即可见
- 这是正常的，微信审核通常在1-3分钟内完成

### Q: 想修改小说风格或字数
- 直接修改 `config.py` 中的 `STYLE_PROMPTS` 字典和 `STORY_MIN_WORDS`/`STORY_MAX_WORDS`

---

## 七、腾讯云 API 开通指引

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 搜索「混元大模型」→ 开通服务
3. 搜索「混元文生图」→ 开通服务
4. 进入「访问管理」→「API密钥管理」→ 新建密钥
5. 将 SecretId 和 SecretKey 填入 `config.py`

---

*最后更新：2026-04-28*
