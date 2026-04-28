#!/usr/bin/env python3
import requests, json, os
from config import HUNYUAN_API_KEY, HUNYUAN_API_BASE

url = f"{HUNYUAN_API_BASE}/chat/completions"
headers = {
    "Authorization": f"Bearer {HUNYUAN_API_KEY}",
    "Content-Type": "application/json",
}
payload = {
    "model": "hunyuan-turbos",
    "messages": [
        {"role": "user", "content": "请用一句话介绍自己，直接输出中文，不要使用\\uXXXX转义。"}
    ],
}

resp = requests.post(url, headers=headers, json=payload, timeout=30)
print("=== raw text of response ===")
print(repr(resp.text[:500]))
print()
result = resp.json()
content = result["choices"][0]["message"]["content"]
print("=== content repr ===")
print(repr(content))
print()
print("=== content (printed) ===")
print(content)
