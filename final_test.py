import requests
import json

# 测试新的Anthropic标准路径
BASE_URL = "http://localhost:8000/anthropic/v1"

print("=== 测试Anthropic标准API路径 ===")

# 测试1：基本请求
print("\n1. 基本请求:")
response = requests.post(f"{BASE_URL}/messages", json={
    "model": "claude-3-haiku-20240307",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 50
})
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"响应: {result['content'][0]['text']}")

# 测试2：带复杂system参数
print("\n2. 带复杂system参数:")
response = requests.post(f"{BASE_URL}/messages", json={
    "model": "claude-3-haiku-20240307",
    "messages": [{"role": "user", "content": "你好"}],
    "system": [
        {"type": "text", "text": "你是一个友好的助手"},
        {"type": "text", "text": "请用简洁的语言回答"}
    ],
    "max_tokens": 50
})
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"响应: {result['content'][0]['text']}")

# 测试3：流式响应
print("\n3. 流式响应:")
response = requests.post(f"{BASE_URL}/messages", json={
    "model": "claude-3-haiku-20240307",
    "messages": [{"role": "user", "content": "用一句话介绍FastAPI"}],
    "max_tokens": 50,
    "stream": True
}, stream=True)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    print("流式内容:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if 'content_block_delta' in line_str:
                try:
                    data = json.loads(line_str[6:])
                    content = data.get('delta', {}).get('text', '')
                    print(content, end='', flush=True)
                except:
                    pass
    print("\n✅ 流式响应完成")

print("\n=== 所有测试完成 ===")