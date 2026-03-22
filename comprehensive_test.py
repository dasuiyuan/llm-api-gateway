import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health_endpoints():
    """测试健康检查端点"""
    print("=== 测试健康检查端点 ===")
    
    # 测试根路径
    response = requests.get(f"{BASE_URL}/")
    print(f"GET /: {response.status_code} - {response.json()}")
    
    # 测试健康检查
    response = requests.get(f"{BASE_URL}/health")
    print(f"GET /health: {response.status_code} - {response.json()}")
    print()

def test_anthropic_switch_basic():
    """测试基本的Anthropic协议转换"""
    print("=== 测试基本Anthropic协议转换 ===")
    
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
    
    response = requests.post(f"{BASE_URL}/anthropic_switch", json=test_data)
    print(f"POST /anthropic_switch: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 协议转换成功")
        print(f"模型: {result['model']}")
        print(f"响应内容: {result['content'][0]['text']}")
        print(f"输入tokens: {result['usage']['input_tokens']}")
        print(f"输出tokens: {result['usage']['output_tokens']}")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

def test_anthropic_switch_with_system():
    """测试带系统提示的Anthropic协议转换"""
    print("=== 测试带系统提示的Anthropic协议转换 ===")
    
    test_data = {
        "model": "claude-3-haiku-20240307",
        "messages": [
            {
                "role": "user",
                "content": "什么是RESTful API？"
            }
        ],
        "max_tokens": 200,
        "temperature": 0.5,
        "system": "你是一个专业的软件开发专家，请用简洁明了的语言回答技术问题。"
    }
    
    response = requests.post(f"{BASE_URL}/anthropic_switch", json=test_data)
    print(f"POST /anthropic_switch: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 带系统提示的协议转换成功")
        print(f"响应内容: {result['content'][0]['text']}")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

def test_anthropic_switch_multi_turn():
    """测试多轮对话"""
    print("=== 测试多轮对话 ===")
    
    # 第一轮对话
    messages = [
        {"role": "user", "content": "你好，我叫小明"},
        {"role": "assistant", "content": "你好，小明！很高兴认识你。有什么我可以帮助你的吗？"},
        {"role": "user", "content": "我叫什么名字？"}
    ]
    
    test_data = {
        "model": "claude-3-haiku-20240307",
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    response = requests.post(f"{BASE_URL}/anthropic_switch", json=test_data)
    print(f"POST /anthropic_switch: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 多轮对话成功")
        print(f"响应内容: {result['content'][0]['text']}")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

def test_error_handling():
    """测试错误处理"""
    print("=== 测试错误处理 ===")
    
    # 测试无效请求
    invalid_data = {
        "invalid": "data"
    }
    
    response = requests.post(f"{BASE_URL}/anthropic_switch", json=invalid_data)
    print(f"无效请求响应: {response.status_code}")
    print()

if __name__ == "__main__":
    print("开始全面测试LLM API Gateway...")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        test_health_endpoints()
        test_anthropic_switch_basic()
        test_anthropic_switch_with_system()
        test_anthropic_switch_multi_turn()
        test_error_handling()
        
        print("✅ 所有测试完成！")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")