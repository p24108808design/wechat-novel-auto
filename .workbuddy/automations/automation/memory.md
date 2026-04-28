# 自动化执行记录 - 微信公众号每日小说自动发布

## 最新执行结果（2026-04-28 15:17）

- **执行状态**: ✅ 成功
- **文章标题**: 《未拆的快递》
- **风格**: 悬疑推理（weekday=1）
- **文案长度**: 1095 字
- **配图**: 成功生成（1575 KB）
- **草稿ID**: `DF0AkBVmTVY1lPCYjbg9mUIOqGonVLNliLaDWOGa-typ0TMXnv9Z4-WCvHWMtciY`
- **提醒**: 草稿已创建，需手动前往微信公众号后台 → 草稿箱发布

## GitHub Actions 云端部署（已配置）

### 新增文件
- `.github/workflows/publish.yml` — 定时每天 UTC 23:50（北京时间 07:50）自动执行
- `config_env.py` — 云端配置，从环境变量读取 API Key
- `requirements.txt` — Python 依赖（仅 requests）
- `.gitignore` — 排除 config.py、debug/、images/、日志等敏感文件

### main.py 改造
- 自动检测 `GITHUB_ACTIONS` 环境变量
- 云端：使用 `config_env.py`（环境变量）
- 本地：使用 `config.py`（本地文件）
- 云端日志仅输出 stdout，不写本地文件

### GitHub Secrets 需配置（7个）
| Secret 名称 | 对应内容 |
|-------------|---------|
| WECHAT_APP_ID | 微信公众号 AppID |
| WECHAT_APP_SECRET | 微信公众号 AppSecret |
| HUNYUAN_API_KEY | 混元 API Key（文案生成） |
| HUNYUAN_API_BASE | `https://api.lkeap.cloud.tencent.com/plan/v3` |
| HUNYUAN_SECRET_ID | 腾讯云 SecretId（文生图） |
| HUNYUAN_SECRET_KEY | 腾讯云 SecretKey（文生图） |
| HUNYUAN_REGION | `ap-guangzhou` |

### 部署步骤
1. 将代码上传到 GitHub 仓库
2. 在仓库 Settings → Secrets → Actions 中配置上述 7 个 Secret
3. 启用 Actions（首次推送自动触发，或手动 Run workflow）
4. 之后每天北京时间 07:50 自动执行，无需电脑开机

### 微信 IP 白名单（如需）
GitHub Actions runner IP 范围不固定，建议在微信公众号后台暂时关闭 IP 白名单限制。

## 历史问题记录

- `401 Unauthorized` — Hunyuan API 密钥配置问题（已通过 lkeap API key 解决）
- `invalid ip ... not in whitelist` — 微信公众平台 IP 白名单问题（GitHub Actions 需关闭白名单）
- `api unauthorized (48001)` — 个人号无群发权限，改为仅创建草稿

## 配置说明

- 本地运行：`python main.py`（依赖 config.py）
- 云端运行：GitHub Actions 自动检测 `GITHUB_ACTIONS` 环境变量
- 日志文件：`publish_log.txt`
