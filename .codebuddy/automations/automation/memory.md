# 自动化执行记录

## 最近执行：2026-04-28 14:55

### 执行结果：✅ 成功

**执行流程**：
1. ✅ 获取今日风格：悬疑推理（weekday=1，周二）
2. ✅ 混元 API 生成文案：《未拆的快递》，1158 字
3. ✅ 混元文生图 API 生成配图：1503 KB
4. ✅ 图片备份：`images/20260428_cover.jpg`（被覆盖）
5. ✅ 微信 access_token 获取成功
6. ✅ 永久图片上传成功
7. ✅ 草稿创建成功

**输出**：
- 文章标题：《未拆的快递》
- 图片 media_id：`DF0AkBVmTVY1lPCYjbg9mahOrPWDJ9uB9GDMOPs1zspzmP6lzqQ8Xp9Z1CY_zXZw`
- 草稿 draft_id：`DF0AkBVmTVY1lPCYjbg9mZ7zYkgSgnfxDbPXMW24ZB_E6CjsgoljaqzXtSWXWcwr`
- 状态：草稿已创建，待手动发布

### 与上次执行（14:42）的差异
- 上次文案：《倒悬的钟摆》（1052 字）
- 本次文案：《未拆的快递》（1158 字）
- 图片大小：1110 KB → 1503 KB
- 同一天内多次运行会覆盖 `images/20260428_cover.jpg`

---

## 历史记录

### 2026-04-28 14:42（成功）

**执行流程**：
1. ✅ 获取今日风格：悬疑推理（weekday=1，周二）
2. ✅ 混元 API 生成文案：《倒悬的钟摆》，1052 字
3. ✅ 混元文生图 API 生成配图：1110 KB
4. ✅ 图片备份：`images/20260428_cover.jpg`
5. ✅ 微信 access_token 获取成功
6. ✅ 永久图片上传成功
7. ✅ 草稿创建成功

**输出**：
- 文章标题：《倒悬的钟摆》
- 图片 media_id：`DF0AkBVmTVY1lPCYjbg9mT_KoTNe2LdahWZ1UMTEUo5LsG6-kwM6S4-S1ppX6zd4`
- 草稿 draft_id：`DF0AkBVmTVY1lPCYjbg9mVuRcEhkKGRUHplhTDVnUjkPf4qerGsazwn6H7HfzuSj`

### 2026-04-28 11:26（失败）

#### 执行结果：失败（API Key 未授权）

**错误信息**：
- `401 Unauthorized`
- `{"error":{"message":"not authorized","code":"not_authorized_error"}}`

**根因**：API Key `sk-tp5DS...` 在 `api.lkeap.cloud.tencent.com/plan/v3` 端点返回 **not_authorized**。
Token Plan 要求的 Key 格式为 `sk-tp-xxx`（带连字符），当前 Key 前缀为 `sk-tp5`，可能格式不符或 Key 已过期/未激活。

#### 已完成的修复
1. ✅ 安装 requests 依赖
2. ✅ 重写 main.py 为 OpenAI 兼容格式（Bearer Token 鉴权）
3. ✅ 修复 Windows GBK 编码问题（SafeStreamHandler）
4. ✅ 修复 datetime.utcfromtimestamp 弃用警告
5. ✅ 模型名改为 hunyuan-turbos（Token Plan 支持的模型）
6. ✅ 微信公众号凭证未配置时优雅跳过（不再崩溃）

#### 待处理
- [x] 用户需确认 API Key 是否有效 / 提供正确的 sk-tp-xxx 格式 Key
- [x] 配置微信公众号 WECHAT_APP_ID / WECHAT_APP_SECRET
- [x] 文生图接口 `/images/generations` 是否被 lkeap 支持（待验证）
