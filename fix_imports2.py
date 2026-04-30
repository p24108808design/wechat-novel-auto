import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 WECHAT_APPSECRET 为 WECHAT_APP_SECRET
content = content.replace('WECHAT_APPSECRET', 'WECHAT_APP_SECRET')

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已修复 WECHAT_APPSECRET 导入")
