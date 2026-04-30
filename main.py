#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号自动发布脚本 - 完整版（含插图功能）
"""

import os
import re
import time
import json
import hashlib
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
import base64
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# 导入配置
from config import (
    WECHAT_APP_ID, WECHAT_APP_SECRET,
    DOUBAO_API_KEY, DOUBAO_API_BASE, DOUBAO_MODEL,
    HUNYUAN_API_KEY, HUNYUAN_API_BASE,
    HUNYUAN_SECRET_ID, HUNYUAN_SECRET_KEY, HUNYUAN_REGION,
    IMAGE_WIDTH, IMAGE_HEIGHT,
    STORY_MIN_WORDS, STORY_MAX_WORDS,
    STYLE_MAP, STYLE_PROMPTS
)

# ========== 日志配置 ==========
LOG_LEVEL = "INFO"
LOG_FILE = "publish_log.txt"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========== 微信公众号 API ==========
class WechatAPI:
    """微信公众号 API 封装"""

    def __init__(self, appid, appsecret):
        self.appid = appid
        self.appsecret = appsecret
        self.access_token = None
        self.base_url = 'https://api.weixin.qq.com'
        # 初始化时获取 access_token
        self.access_token = self._get_access_token()

    def _parse_json_response(self, response):
        """正确解析微信API的JSON响应（强制UTF-8解码）"""
        return json.loads(response.content.decode('utf-8'))

    def _get_access_token(self):
        """获取 access_token"""
        url = f'{self.base_url}/cgi-bin/token'
        params = {
            'grant_type': 'client_credential',
            'appid': self.appid,
            'secret': self.appsecret
        }
        response = requests.get(url, params=params, timeout=30)
        result = self._parse_json_response(response)

        if 'access_token' in result:
            logger.info('获取 access_token 成功')
            return result['access_token']
        else:
            logger.error(f'获取 access_token 失败: {result}')
            raise Exception(f'获取 access_token 失败: {result}')

    def upload_image(self, image_path):
        """上传图片到微信（返回 URL）"""
        url = f'{self.base_url}/cgi-bin/material/add_material'
        params = {
            'access_token': self.access_token,
            'type': 'image'
        }

        with open(image_path, 'rb') as f:
            files = {'media': f}
            response = requests.post(url, params=params, files=files, timeout=60)
            result = self._parse_json_response(response)

        if 'media_id' in result:
            logger.info(f'图片上传成功: {result.get("url")}')
            return result['media_id'], result.get('url')
        else:
            logger.error(f'图片上传失败: {result}')
            raise Exception(f'图片上传失败: {result}')

    def create_draft(self, title, content, author='', thumb_media_id=None):
        """创建草稿"""
        # 微信标题限制：UTF-8 编码不超过 64 字节
        title_bytes = title.encode('utf-8')
        logger.info(f'标题调试: 字符数={len(title)}, 字节数={len(title_bytes)}, repr={repr(title)}')
        
        if len(title_bytes) > 64:
            # 安全截断到 64 字节以内
            truncated = title_bytes[:64]
            while truncated and (truncated[-1] & 0b11000000) == 0b10000000:
                truncated = truncated[:-1]
            if not truncated:
                truncated = title_bytes[:3]
            title = truncated.decode('utf-8', errors='ignore')
            logger.warning(f'标题过长已截断: {title}')
        
        # 摘要也需要限制（64 字符）- 使用纯文本，并强制限制长度
        import re
        text_content = re.sub('<[^<]+?>', '', content)  # 移除 HTML 标签
        digest = text_content[:50]
        # 清理摘要中的特殊字符和换行符
        digest = digest.replace('\n', '').replace('\r', '')
        digest = re.sub(r'[""' '「」【】《》]', '', digest)
        
        # 摘要限制：UTF-8 编码不超过 60 字节（留点余量）
        digest = digest[:20]  # 先按字符数粗略截断（20 中文字符 = 60 字节）
        digest_bytes = digest.encode('utf-8')
        if len(digest_bytes) > 60:
            # 精确截断到 60 字节以内
            truncated = digest_bytes[:60]
            while truncated and (truncated[-1] & 0b11000000) == 0b10000000:
                truncated = truncated[:-1]
            if not truncated:
                truncated = digest_bytes[:3]
            digest = truncated.decode('utf-8', errors='ignore')
            logger.warning(f'摘要过长已截断: {digest}')
        
        digest_bytes = digest.encode('utf-8')  # 重新计算字节数
        
        logger.info(f'摘要调试: 字符数={len(digest)}, 字节数={len(digest_bytes)}, repr={repr(digest[:20])}')
        
        # 作者名限制（8 字节）
        author_bytes = author.encode('utf-8')
        if len(author_bytes) > 8:
            truncated = author_bytes[:8]
            while truncated and (truncated[-1] & 0b11000000) == 0b10000000:
                truncated = truncated[:-1]
            author = truncated.decode('utf-8', errors='ignore')
            logger.warning(f'作者名过长已截断: {author}')

        url = f'{self.base_url}/cgi-bin/draft/add'
        params = {'access_token': self.access_token}

        articles = [{
            'title': title,
            'author': author,
            'digest': digest,
            'content': content,
            'content_source_url': '',
            'thumb_media_id': thumb_media_id or '',
            'need_open_comment': 1,
            'only_fans_can_comment': 0
        }]

        data = {'articles': articles}
        # 调试：打印请求体（截断 content）
        debug_articles = []
        for art in articles:
            debug_art = art.copy()
            debug_art['content'] = debug_art['content'][:100] + '...'
            debug_articles.append(debug_art)
        logger.info(f'草稿请求体: {json.dumps({"articles": debug_articles}, ensure_ascii=False)}')
        
        # 手动序列化 JSON，确保中文不被转义
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        logger.info(f'发送草稿请求 (前100字符): {json_str[:100]}...')
        
        response = requests.post(url, params=params, data=json_str.encode('utf-8'), headers=headers, timeout=30)
        result = self._parse_json_response(response)

        if 'media_id' in result:
            logger.info(f'草稿创建成功: {result.get("media_id")}')
            return result['media_id']
        elif result.get('errcode', 0) != 0:
            logger.error(f'草稿创建失败: {result}')
            raise Exception(f'草稿创建失败: {result}')
        else:
            logger.error(f'草稿创建失败: {result}')
            raise Exception(f'草稿创建失败: {result}')

    def publish_draft(self, media_id):
        """发布草稿"""
        url = f'{self.base_url}/cgi-bin/freepublish/submit'
        params = {'access_token': self.access_token}

        data = {'media_id': media_id}
        response = requests.post(url, params=params, json=data, timeout=30)
        result = self._parse_json_response(response)

        if result.get('errcode') == 0:
            logger.info(f'发布成功: {result.get("publish_id")}')
            return result['publish_id']
        else:
            logger.error(f'发布失败: {result}')
            raise Exception(f'发布失败: {result}')


# ========== 豆包 API ==========
class DoubaoAPI:
    """豆包大模型 API 封装（OpenAI 兼容接口，用于文本生成）"""

    def __init__(self, api_key, api_base, model):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def generate_text(self, prompt, max_tokens=800):
        """使用 OpenAI 兼容接口生成文本"""
        try:
            url = f"{self.api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }

            response = requests.post(url, headers=headers, json=data, timeout=60)
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.info('豆包 API 文本生成成功')
                return content
            else:
                logger.error(f'豆包 API 返回错误: {result}')
                raise Exception(f'豆包 API 返回错误: {result}')

        except Exception as e:
            logger.error(f'豆包 API 调用失败: {e}')
            raise


# ========== Pollinations.ai API ==========
class PollinationsAPI:
    """Pollinations.ai API 封装（完全免费，无需API Key）"""

    def __init__(self):
        self.base_url = "https://image.pollinations.ai/prompt"

    def generate_image(self, prompt, style_config, width=1024, height=1024):
        """使用 Pollinations.ai 生成图片（免费）- 支持重试"""
        max_retries = 2
        retry_delay = 5

        for attempt in range(max_retries + 1):
            try:
                # 构建完整提示词
                full_prompt = f"{style_config.get('image_prompt', '')}, {prompt}"

                # 清理提示词中的特殊字符（用于URL）
                import urllib.parse
                safe_prompt = urllib.parse.quote(full_prompt)

                # 构建请求URL
                url = f"{self.base_url}/{safe_prompt}?width={width}&height={height}&nologo=true"

                logger.info(f'Pollinations.ai 生成图片 (尝试 {attempt+1}/{max_retries+1}): {prompt[:50]}...')
                logger.info(f'请求URL: {url[:100]}...')

                # 发送请求获取图片（增加超时时间到120秒）
                response = requests.get(url, timeout=120)
                response.raise_for_status()

                # 返回图片的二进制数据（Pollinations直接返回图片）
                image_data = response.content
                image_b64 = base64.b64encode(image_data).decode('utf-8')

                logger.info('Pollinations.ai 图片生成成功')
                return image_b64

            except Exception as e:
                logger.error(f'Pollinations.ai 生成图片失败 (尝试 {attempt+1}/{max_retries+1}): {e}')
                if attempt < max_retries:
                    logger.info(f'等待 {retry_delay} 秒后重试...')
                    time.sleep(retry_delay)
                else:
                    logger.error('Pollinations.ai 所有重试均失败')
                    raise


# ========== 混元 API ==========
class HunyuanAPI:
    """腾讯混元 API 封装（支持文本生成和图片生成）"""

    def __init__(self, api_key, api_base, secret_id, secret_key, region):
        self.api_key = api_key
        self.api_base = api_base
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region

    def generate_text(self, prompt, max_tokens=800):
        """使用 OpenAI 兼容接口生成文本"""
        try:
            url = f"{self.api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "hunyuan-turbos",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }

            response = requests.post(url, headers=headers, json=data, timeout=60)
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.info('混元 API 文本生成成功')
                return content
            else:
                logger.error(f'混元 API 返回错误: {result}')
                raise Exception(f'混元 API 返回错误: {result}')

        except Exception as e:
            logger.error(f'混元 API 调用失败: {e}')
            raise

    def generate_image(self, prompt, style_config):
        """生成图片（使用文生图 API）"""
        try:
            # 构建图片生成提示词
            full_prompt = f"{style_config.get('image_prompt', '')}, {prompt}"

            # 调用文生图 API
            url = "https://hunyuan.tencentcloudapi.com"
            service = "hunyuan"
            action = "TextToImageLite"
            version = "2023-09-01"
            region = self.region

            # 构建请求体
            payload = {
                "Prompt": full_prompt[:512],  # API 限制 512 字符
                "Style": "000",
                "Resolution": "1024:1024"
            }

            # TC3 签名
            import hmac
            import hashlib
            from datetime import datetime, timezone
            import time

            timestamp = int(time.time())
            date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

            # 构建规范请求串
            http_request_method = "POST"
            canonical_uri = "/"
            canonical_querystring = ""
            canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{url.split('//')[1]}\nx-tc-action:{action.lower()}\n"
            signed_headers = "content-type;host;x-tc-action"
            hashed_request_payload = hashlib.sha256(
                json.dumps(payload).encode('utf-8')
            ).hexdigest()
            canonical_request = (
                f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n"
                f"{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
            )

            # 构建待签名字符串
            algorithm = "TC3-HMAC-SHA256"
            credential_scope = f"{date}/{service}/tc3_request"
            hashed_canonical_request = hashlib.sha256(
                canonical_request.encode('utf-8')
            ).hexdigest()
            string_to_sign = (
                f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
            )

            # 计算签名
            def sign(key, msg):
                return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

            secret_date = sign(('TC3' + self.secret_key).encode('utf-8'), date)
            secret_service = sign(secret_date, service)
            secret_signing = sign(secret_service, 'tc3_request')
            signature = hmac.new(
                secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256
            ).hexdigest()

            # 构建 Authorization
            authorization = (
                f"{algorithm} Credential={self.secret_id}/{credential_scope}, "
                f"SignedHeaders={signed_headers}, Signature={signature}"
            )

            # 发送请求
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json; charset=utf-8",
                "Host": url.split('//')[1],
                "X-TC-Action": action,
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Version": version,
                "X-TC-Region": region
            }

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            result = response.json()

            if 'Response' in result:
                response_data = result['Response']
                if 'Result' in response_data and 'ImageUrls' in response_data['Result']:
                    # 返回 base64 编码的图片
                    image_b64 = response_data['Result']['ImageUrls'][0]
                    return image_b64
                elif 'ResultImage' in response_data:
                    # 返回 base64 编码的图片数据
                    image_b64 = response_data['ResultImage']
                    return image_b64
                else:
                    logger.error(f'图片生成失败: {response_data}')
                    raise Exception(f'图片生成失败: {response_data}')
            else:
                logger.error(f'API 返回错误: {result}')
                raise Exception(f'API 返回错误: {result}')

        except Exception as e:
            logger.error(f'生成图片失败: {e}')
            raise


# ========== 核心功能 ==========
def parse_image_markers(text):
    """
    解析文本中的 [IMAGE: 场景描述] 标记
    返回: (clean_text, image_descs)
    """
    pattern = r'\[IMAGE:\s*(.+?)\]'
    image_descs = re.findall(pattern, text)
    clean_text = re.sub(pattern, '', text)
    return clean_text.strip(), image_descs


def generate_story(style_name, api):
    """生成故事内容，返回 (title, body, image_descs)"""
    style_config = STYLE_PROMPTS[style_name]
    prompt = style_config['story_prompt']

    logger.info(f'开始生成 {style_config["name"]} 风格的内容...')
    content = api.generate_text(prompt, max_tokens=1200)

    # 解析标题和正文
    lines = content.strip().split('\n')
    title = lines[0].strip()
    # 移除 Markdown 加粗标记
    title = title.replace('**', '')
    body_start = 2 if lines[1].strip() == '' else 1
    body = '\n'.join(lines[body_start:])

    # 解析图片标记
    clean_body, image_descs = parse_image_markers(body)

    logger.info(f'生成标题: {title}')
    logger.info(f'正文长度: {len(clean_body)} 字符')
    logger.info(f'插图场景数: {len(image_descs)}')

    return title, clean_body, image_descs


def generate_cover_image(style_name, api):
    """生成封面图"""
    style_config = STYLE_PROMPTS[style_name]
    prompt = style_config.get('image_prompt', '唯美风景，高质量摄影')

    logger.info('开始生成封面图...')
    image_b64 = api.generate_image(prompt, style_config)

    # 保存图片
    image_dir = Path('images')
    image_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_path = image_dir / f'cover_{timestamp}.jpg'

    with open(image_path, 'wb') as f:
        f.write(base64.b64decode(image_b64))

    logger.info(f'封面图已保存: {image_path}')
    return str(image_path)


def generate_illustration(style_name, scene_desc, api):
    """为场景生成插图"""
    style_config = STYLE_PROMPTS[style_name]
    illustration_prompt = style_config.get('illustration_prompt', '唯美场景，高质量摄影')

    # 组合提示词：风格 + 场景描述
    full_prompt = f"{illustration_prompt}，{scene_desc}"

    logger.info(f'生成插图: {scene_desc}')
    image_b64 = api.generate_image(full_prompt, style_config)

    # 保存图片
    image_dir = Path('images')
    image_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = hashlib.md5(scene_desc.encode()).hexdigest()[:6]
    image_path = image_dir / f'illustration_{timestamp}_{random_suffix}.jpg'

    with open(image_path, 'wb') as f:
        f.write(base64.b64decode(image_b64))

    logger.info(f'插图已保存: {image_path}')
    return str(image_path)


def text_to_wechat_html(title, text, image_urls=None):
    """
    将纯文本转换为微信公众号 HTML 格式
    支持在正文中间插入图片
    """
    # 基础样式
    html_template = """<section style="font-size: 15px; line-height: 2; color: #333; padding: 10px 15px;">
{content}
</section>"""

    # 分段处理
    paragraphs = text.split('\n\n')
    content_parts = []

    img_index = 0
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # 每 2-3 段插入一张图片（如果有图片的话）
        if image_urls and img_index < len(image_urls):
            if i > 0 and i % 2 == 0 and img_index < len(image_urls):
                img_tag = f'<p style="text-align: center;"><img src="{image_urls[img_index]}" style="max-width: 100%; height: auto;"></p>'
                content_parts.append(img_tag)
                img_index += 1

        # 处理正文段落
        if para.startswith('# '):
            # 一级标题
            content_parts.append(f'<h2 style="color: #1a1a1a; margin: 20px 0 10px;">{para[2:]}</h2>')
        elif para.startswith('## '):
            # 二级标题
            content_parts.append(f'<h3 style="color: #333; margin: 15px 0 8px;">{para[3:]}</h3>')
        else:
            # 普通段落
            content_parts.append(f'<p style="margin: 10px 0; text-indent: 2em;">{para}</p>')

    # 如果还有剩余的图片，追加到末尾
    while img_index < len(image_urls or []):
        img_tag = f'<p style="text-align: center;"><img src="{image_urls[img_index]}" style="max-width: 100%; height: auto;"></p>'
        content_parts.append(img_tag)
        img_index += 1

    content = '\n'.join(content_parts)
    return html_template.format(content=content)


def run():
    """主运行流程"""
    logger.info('=' * 50)
    logger.info('微信公众号自动发布脚本启动')
    logger.info(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info('=' * 50)

    try:
        # 1. 初始化 API
        # 豆包 API（用于文本生成）
        if not DOUBAO_API_KEY:
            logger.error('豆包 API Key 未配置，请在 config.py 中填写 DOUBAO_API_KEY')
            raise Exception('豆包 API Key 未配置')
        doubao = DoubaoAPI(DOUBAO_API_KEY, DOUBAO_API_BASE, DOUBAO_MODEL)

        # Pollinations.ai（免费图片生成，无需API Key）
        pollinations = PollinationsAPI()
        logger.info('使用 Pollinations.ai 免费生成图片')

        # 微信公众号 API
        wechat = WechatAPI(WECHAT_APP_ID, WECHAT_APP_SECRET)

        # 2. 选择风格（基于星期几）
        weekday = datetime.now().weekday()
        style_name = STYLE_MAP.get(weekday, "mixed")
        style_config = STYLE_PROMPTS[style_name]
        logger.info(f'本次使用风格: {style_config["name"]} (weekday={weekday})')

        # 3. 生成故事内容（使用豆包 API 生成文本）
        title, body_text, image_descs = generate_story(style_name, doubao)
        
        # 清理标题中的特殊字符（微信 API 可能不支持）
        import re
        title = re.sub(r'[「」《》【】]', '', title)
        logger.info(f'清理后标题: {title}')
        
        logger.info(f'标题: {title}')
        logger.info(f'需要生成的插图数: {len(image_descs)}')

        # 4. 生成封面图
        cover_path = generate_cover_image(style_name, pollinations)
        logger.info(f'封面图: {cover_path}')

        # 5. 上传封面图
        cover_media_id, cover_url = wechat.upload_image(cover_path)
        logger.info(f'封面图上传成功: media_id={cover_media_id}')

        # 6. 生成并上传插图（1张，节省配额）
        illustration_urls = []
        for i, desc in enumerate(image_descs[:1]):  # 最多1张
            try:
                illustration_path = generate_illustration(style_name, desc, pollinations)
                media_id, url = wechat.upload_image(illustration_path)
                if url:
                    illustration_urls.append(url)
                    logger.info(f'插图 {i+1} 上传成功: {url[:50]}...')
                else:
                    logger.warning(f'插图 {i+1} 上传后未返回 URL')
                time.sleep(1)  # 避免 API 限流
            except Exception as e:
                logger.error(f'插图 {i+1} 生成失败: {e}')

        logger.info(f'成功生成 {len(illustration_urls)} 张插图')

        # 7. 转换为 HTML（插入插图）
        html_content = text_to_wechat_html(title, body_text, illustration_urls)
        logger.info('HTML 转换完成')

        # 8. 创建草稿
        media_id = wechat.create_draft(
            title=title,
            content=html_content,
            author='AI助手',
            thumb_media_id=cover_media_id
        )
        logger.info(f'草稿创建成功: {media_id}')
        logger.info(f'请手动前往微信公众号后台 → 草稿箱 发布文章')
        logger.info(f'草稿链接: https://mp.weixin.qq.com')

        logger.info('=' * 50)
        logger.info('任务完成！草稿已创建，请手动发布。')
        logger.info('=' * 50)

    except Exception as e:
        logger.error(f'运行失败: {e}', exc_info=True)
        raise


if __name__ == '__main__':
    run()
