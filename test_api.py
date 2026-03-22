import requests
import json

# 测试健康检查端点
print("测试健康检查端点...")
try:
    response = requests.get("http://localhost:8000/")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
except Exception as e:
    print(f"错误: {e}")

# 测试健康检查端点
print("\n测试健康检查端点...")
try:
    response = requests.get("http://localhost:8000/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
except Exception as e:
    print(f"错误: {e}")

# 测试anthropic_switch接口（使用示例数据）
print("\n测试anthropic_switch接口...")
test_data = {
    "model": "claude-3-haiku-20240307",
    "messages": [
        {
            "role": "user",
            "content": "你好，请用一句话介绍一下FastAPI"
        }
    ],
    "max_tokens": 100,
    "temperature": 0.7
}

try:
    response = requests.post("http://localhost:8000/messages", json=test_data)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print("响应格式正确，Anthropic协议转换成功")
        print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    else:
        print(f"错误响应: {response.text}")
except Exception as e:
    print(f"错误: {e}")