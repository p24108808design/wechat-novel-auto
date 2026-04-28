#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号每日短篇小说自动发布脚本
功能：自动生成小说文案 + AI配图 → 发布到微信公众号
运行方式：python main.py
"""

import sys
import json
import time
import base64
import datetime
import logging
import os
import re
import requests

# ── 配置 ──────────────────────────────────────────────
# GitHub Actions 环境优先用 config_env.py（从环境变量读取）
# 本地开发优先用 config.py（从文件读取）
import os as _os
if _os.environ.get("GITHUB_ACTIONS") or _os.environ.get("CI"):
    from config_env import (
        WECHAT_APP_ID, WECHAT_APP_SECRET,
        HUNYUAN_API_KEY, HUNYUAN_API_BASE,
        HUNYUAN_SECRET_ID, HUNYUAN_SECRET_KEY, HUNYUAN_REGION,
        IMAGE_WIDTH, IMAGE_HEIGHT,
        STORY_MIN_WORDS, STORY_MAX_WORDS,
        STYLE_MAP, STYLE_PROMPTS,
    )
else:
    from config import (
        WECHAT_APP_ID, WECHAT_APP_SECRET,
        HUNYUAN_API_KEY, HUNYUAN_API_BASE,
        HUNYUAN_SECRET_ID, HUNYUAN_SECRET_KEY, HUNYUAN_REGION,
        IMAGE_WIDTH, IMAGE_HEIGHT,
        STORY_MIN_WORDS, STORY_MAX_WORDS,
        STYLE_MAP, STYLE_PROMPTS,
    )

# ── 日志配置 ───────────────────────────────────────────
# GitHub Actions 环境：输出到 stdout，CI 平台会捕获
_is_cloud = os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI")
_log_file = os.environ.get("LOG_FILE", "publish_log.txt")

if _is_cloud:
    # 云端：只输出到 stdout，CI 平台自动收集
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
else:
    # 本地：同时输出到文件和 stdout
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                try:
                    stream.write(msg + self.terminator)
                except UnicodeEncodeError:
                    safe_msg = msg.encode("gbk", errors="replace").decode("gbk")
                    stream.write(safe_msg + self.terminator)
            except Exception:
                self.handleError(record)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(_log_file, encoding="utf-8"),
            SafeStreamHandler(sys.stdout),
        ],
    )
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
#  1. 获取当日风格
# ══════════════════════════════════════════════════════
def get_today_style() -> dict:
    weekday = datetime.datetime.now().weekday()  # 0=周一
    style_key = STYLE_MAP.get(weekday, "healing")
    style = STYLE_PROMPTS[style_key]
    log.info(f"今日风格: {style['name']}（weekday={weekday}）")
    return style


# ══════════════════════════════════════════════════════
#  2. 调用混元生成小说文案（OpenAI 兼容格式）
# ══════════════════════════════════════════════════════
def generate_story(style: dict) -> tuple[str, str]:
    """
    返回 (title, body_html)
    使用 OpenAI 兼容接口（api.lkeap.cloud.tencent.com）
    """
    prompt = style["story_prompt"].format(
        min_words=STORY_MIN_WORDS, max_words=STORY_MAX_WORDS
    )

    url = f"{HUNYUAN_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {HUNYUAN_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "hunyuan-turbos",
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    log.info("正在调用混元 API 生成小说文案...")
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()

    # 检查 API 错误
    if "error" in result:
        error_info = result["error"]
        raise RuntimeError(f"混元 API 错误: {error_info.get('code', '')} - {error_info.get('message', '')}")

    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError(f"混元 API 返回无 choices，完整响应: {result}")

    raw_text = choices[0]["message"]["content"]
    log.info(f"API返回原始内容(前200字): {repr(raw_text[:200])}")
    # 处理 API 可能返回的 Unicode 转义序列（如 \u6d88 → 消）
    if r"\u" in raw_text:
        def _decode_unicode_escape(m):
            return chr(int(m.group(1), 16))
        raw_text = re.sub(r'\\u([0-9a-fA-F]{4})', _decode_unicode_escape, raw_text)
        log.info("⚠️ 检测到 Unicode 转义，已自动解码")
    log.info(f"文案生成成功，长度: {len(raw_text)} 字")

    # ── 解析标题和正文 ──
    lines = raw_text.strip().splitlines()
    title = lines[0].strip().lstrip("#").strip()
    # 清理标题中的 Markdown 加粗符号和多余书名号
    title = title.strip("*").strip().strip("《》").strip("*")
    body_lines = lines[2:] if len(lines) > 2 else lines[1:]
    body_html = _text_to_wechat_html(title, "\n".join(body_lines), style["name"])
    # 调试：将生成的内容写入文件，方便检查
    _debug_save(raw_text, body_html, title)

    return title, body_html


def _debug_save(raw_text: str, body_html: str, title: str):
    """将生成的内容保存到文件，方便检查乱码问题（云端跳过）"""
    if _is_cloud:
        return  # GitHub Actions 不需要本地调试文件
    import datetime as _dt
    today = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("debug", exist_ok=True)
    with open(f"debug/{today}_raw.txt", "w", encoding="utf-8") as f:
        f.write(f"=== 标题 ===\n{title}\n\n=== 原始文案 ===\n{raw_text}\n")
    with open(f"debug/{today}_html.html", "w", encoding="utf-8") as f:
        f.write(body_html)
    log.info(f"调试文件已保存: debug/{today}_raw.txt")


def _text_to_wechat_html(title: str, body: str, style_name: str) -> str:
    """将纯文本正文转为适合微信的 HTML 格式"""
    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    html_paragraphs = "".join(
        f'<p style="margin:0 0 1.2em 0;line-height:1.9;font-size:16px;color:#333;">{p}</p>'
        for p in paragraphs
    )

    return f"""<section style="max-width:680px;margin:0 auto;padding:20px;font-family:'PingFang SC','Microsoft YaHei',sans-serif;">
  <p style="text-align:center;color:#999;font-size:13px;margin-bottom:24px;">
    ✦ 每日短篇 · {style_name} ✦
  </p>
  {html_paragraphs}
  <p style="text-align:center;color:#bbb;font-size:12px;margin-top:32px;">
    — END —
  </p>
</section>"""


# ══════════════════════════════════════════════════════
#  3. 调用混元文生图（TC3 原生接口）
# ══════════════════════════════════════════════════════
def generate_image(style: dict) -> bytes:
    """
    返回图片二进制数据（JPEG）
    使用腾讯云混元原生 TC3 签名方式调用 TextToImageLite
    """
    import hashlib
    import hmac

    # 尝试从 config 获取 TC3 密钥，如果没有则回退到 lkeap
    try:
        secret_id = HUNYUAN_SECRET_ID
        secret_key = HUNYUAN_SECRET_KEY
        region = HUNYUAN_REGION
    except NameError:
        secret_id = ""
        secret_key = ""
        region = "ap-guangzhou"

    # 如果没有配置 TC3 密钥，使用本地 fallback 方式
    if not secret_id or secret_id.startswith("YOUR_"):
        return _generate_image_fallback(style)

    host = "hunyuan.tencentcloudapi.com"
    service = "hunyuan"
    action = "TextToImageLite"
    version = "2023-09-01"
    timestamp = int(time.time())
    date = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).strftime("%Y-%m-%d")

    payload = json.dumps({
        "Prompt": style["image_prompt"],
        "Resolution": f"{IMAGE_WIDTH}:{IMAGE_HEIGHT}",
    })

    signed_headers = "content-type;host;x-tc-action"
    canonical_request = "\n".join([
        "POST", "/", "",
        f"content-type:application/json\nhost:{host}\nx-tc-action:{action.lower()}\n",
        signed_headers,
        hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    ])

    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = "\n".join([
        "TC3-HMAC-SHA256", str(timestamp), credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    def _hmac_sha256(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, service)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }

    log.info("正在调用混元文生图 API 生成配图...")
    resp = requests.post(f"https://{host}", headers=headers, data=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()

    if "Error" in result.get("Response", {}):
        error_info = result["Response"]["Error"]
        raise RuntimeError(f"混元文生图 API 错误: {error_info.get('Code')} - {error_info.get('Message')}")

    b64_image = result["Response"].get("ResultImage")
    if not b64_image:
        raise RuntimeError(f"混元文生图返回无 ResultImage，完整响应: {result}")
    image_bytes = base64.b64decode(b64_image)
    log.info(f"图片生成成功，大小: {len(image_bytes) // 1024} KB")
    return image_bytes


def _generate_image_fallback(style: dict) -> bytes:
    """
    Fallback：当没有 TC3 密钥时，使用 requests 下载一个纯色占位图
    实际生产环境应配置 TC3 密钥或接入其他图片服务
    """
    import struct
    import zlib

    log.warning("未检测到腾讯云 TC3 密钥，使用 fallback 占位图")

    width, height = IMAGE_WIDTH, IMAGE_HEIGHT

    # 生成一个深蓝色渐变 JPEG 占位图（最小有效 JPEG）
    raw_data = b""
    for y in range(height):
        row = b"\x00" + bytes(int(40 + (y / height) * 30)) * 3 * width
        raw_data += row

    def create_jpeg(width, height, color=(30, 50, 90)):
        """创建最小有效 JPEG 图片"""
        from PIL import Image as PILImage
        import io
        img = PILImage.new('RGB', (width, height), color)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()

    try:
        image_bytes = create_jpeg(width, height)
    except ImportError:
        # 如果没有 Pillow，生成最简单的纯色 PNG
        import io
        def create_png(w, h, r, g, b):
            header = b'\x89PNG\r\n\x1a\n'
            ihdr_data = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
            ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

            raw_row = b'\x00' + bytes([r, g, b]) * w
            idat_data = (raw_row * h)
            compressed = zlib.compress(idat_data)
            idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
            idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
            iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
            return header + ihdr + idat + iend

        image_bytes = create_png(width, height, 30, 50, 90)

    log.info(f"Fallback 占位图已生成，大小: {len(image_bytes) // 1024} KB")
    return image_bytes


# ══════════════════════════════════════════════════════
#  4. 微信公众号 API 工具
# ══════════════════════════════════════════════════════
class WechatPublisher:
    BASE = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self):
        self._access_token = None
        self._token_expires = 0

    @property
    def access_token(self) -> str:
        if time.time() < self._token_expires:
            return self._access_token

        log.info("正在获取微信 access_token...")
        url = f"{self.BASE}/token"
        resp = requests.get(url, params={
            "grant_type": "client_credential",
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET,
        }, timeout=30)
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data}")
        self._access_token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"] - 60
        log.info("access_token 获取成功")
        return self._access_token

    def upload_image(self, image_bytes: bytes, filename: str = "cover.jpg") -> str:
        """上传图片素材，返回 media_id"""
        log.info("正在上传封面图片到微信素材库...")
        url = f"https://api.weixin.qq.com/cgi-bin/media/upload"
        resp = requests.post(
            url,
            params={"access_token": self.access_token, "type": "image"},
            files={"media": (filename, image_bytes, "image/jpeg")},
            timeout=60,
        )
        data = resp.json()
        if "media_id" not in data:
            raise RuntimeError(f"上传图片失败: {data}")
        media_id = data["media_id"]
        log.info(f"图片上传成功，media_id: {media_id}")
        return media_id

    def upload_permanent_image(self, image_bytes: bytes, filename: str = "cover.jpg") -> tuple[str, str]:
        """上传永久图片素材，返回 (media_id, url)"""
        log.info("正在上传永久封面图片...")
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material"
        resp = requests.post(
            url,
            params={"access_token": self.access_token, "type": "image"},
            files={"media": (filename, image_bytes, "image/jpeg")},
            timeout=60,
        )
        data = resp.json()
        if "media_id" not in data:
            raise RuntimeError(f"上传永久图片失败: {data}")
        log.info(f"永久图片上传成功，media_id: {data['media_id']}")
        return data["media_id"], data.get("url", "")

    def create_draft(self, title: str, content_html: str,
                     thumb_media_id: str, digest: str = "") -> str:
        """创建草稿，返回 media_id"""
        log.info(f"正在创建草稿：《{title}》...")
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add"
        today = datetime.datetime.now().strftime("%Y年%m月%d日")
        article = {
            "title": title,
            "author": "AI",
            "digest": digest or f"{today} · 每日短篇小说",
            "content": content_html,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
        }
        # 注意：必须用 ensure_ascii=False，否则中文会被转成 \uXXXX，
        # 微信 API 无法正确解码，导致草稿内容显示为 Unicode 转义字符
        json_payload = json.dumps({"articles": [article]}, ensure_ascii=False)
        resp = requests.post(
            url,
            params={"access_token": self.access_token},
            data=json_payload.encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=30,
        )
        data = resp.json()
        if "media_id" not in data:
            raise RuntimeError(f"创建草稿失败: {data}")
        draft_id = data["media_id"]
        log.info(f"草稿创建成功，draft_id: {draft_id}")
        return draft_id

    def publish_draft(self, draft_media_id: str) -> str:
        """发布草稿（群发），返回 publish_id"""
        log.info("正在发布文章...")
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit"
        resp = requests.post(
            url,
            params={"access_token": self.access_token},
            json={"media_id": draft_media_id},
            timeout=30,
        )
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"发布失败: {data}")
        publish_id = data.get("publish_id", "unknown")
        log.info(f"文章发布成功！publish_id: {publish_id}")
        return publish_id


# ══════════════════════════════════════════════════════
#  5. 主流程
# ══════════════════════════════════════════════════════
def run():
    log.info("=" * 50)
    log.info(f"开始执行每日自动发布任务 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 50)

    try:
        # Step 1: 获取今日风格
        style = get_today_style()

        # Step 2: 生成小说文案
        title, body_html = generate_story(style)
        log.info(f"文章标题：《{title}》")

        # Step 3: 生成配图
        image_bytes = generate_image(style)

        # 保存图片备份（云端保存到临时目录）
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        img_path = f"{today_str}_cover.jpg"
        with open(img_path, "wb") as f:
            f.write(image_bytes)
        log.info(f"封面图片已保存: {img_path}")

        # GitHub Actions: 输出关键信息供后续 step 使用
        if _is_cloud:
            gha_output = os.environ.get("GITHUB_OUTPUT", "/tmp/github_output")
            with open(gha_output, "a", encoding="utf-8") as f:
                f.write(f"article_title={title}\n")
                f.write(f"article_date={today_str}\n")
            log.info("GitHub Actions 输出已写入 GITHUB_OUTPUT")

        # Step 4: 上传图片并创建草稿（个人号无认证，仅创建草稿，手动发布）
        if not WECHAT_APP_ID or WECHAT_APP_ID == "YOUR_APPID_HERE":
            log.warning("⚠️ 微信公众号凭证未配置，跳过上传和发布步骤")
            log.info(f"✅ 文案和配图已生成，标题：《{title}》，图片: {img_path}")
        else:
            publisher = WechatPublisher()
            # 使用临时图片上传（无需 IP 白名单），返回的 media_id 可直接作为 thumb_media_id
            thumb_media_id = publisher.upload_image(image_bytes)
            draft_id = publisher.create_draft(title, body_html, thumb_media_id)

            log.info("=" * 50)
            log.info(f"✅ 草稿创建成功！标题：《{title}》/ draft_id: {draft_id}")
            log.info("   请前往微信公众号后台 → 草稿箱 手动发布")
            log.info("=" * 50)

    except Exception as e:
        log.error(f"❌ 发布失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
