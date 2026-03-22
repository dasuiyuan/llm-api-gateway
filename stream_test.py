import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_non_streaming():
    """测试非流式响应"""
    print("=== 测试非流式响应 ===")
    
    test_data = {
        "model": "claude-3-haiku-20240307",
        "messages": [
            {
                "role": "user",
                "content": "你好，请用一句话介绍一下FastAPI"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False
    }
    
    response = requests.post(f"{BASE_URL}/anthropic/v1/messages", json=test_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 非流式响应成功")
        print(f"响应内容: {result['content'][0]['text']}")
        print(f"模型: {result['model']}")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

def test_streaming():
    """测试流式响应"""
    print("=== 测试流式响应 ===")
    
    test_data = {
        "model": "claude-3-haiku-20240307",
        "messages": [
            {
                "role": "user",
                "content": "你好，请用一句话介绍一下FastAPI"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": True
    }
    
    response = requests.post(f"{BASE_URL}/anthropic/v1/messages", json=test_data, stream=True)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 流式响应成功")
        print("响应内容:")
        
        full_content = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if data.get('type') == 'content_block_delta':
                            content = data.get('delta', {}).get('text', '')
                            print(content, end='', flush=True)
                            full_content += content
                        elif data.get('type') == 'message_start':
                            print(f"开始消息: {data.get('message', {}).get('id')}")
                        elif data.get('type') == 'message_stop':
                            print("\n🔄 流式响应完成")
                    except json.JSONDecodeError:
                        continue
        
        print(f"\n完整内容: {full_content}")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

if __name__ == "__main__":
    print("开始测试流式和非流式响应...")
    print("=" * 50)
    
    try:
        test_non_streaming()
        test_streaming()
        print("✅ 所有测试完成！")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")