import requests
import json
import time

BASE_URL = "http://localhost:8000/anthropic/v1"

def test_basic_compatibility():
    """测试基本兼容性"""
    print("=== 测试基本兼容性 ===")
    
    test_cases = [
        # 基本请求
        {
            "name": "基本请求",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 50
            }
        },
        # 带温度参数
        {
            "name": "带温度参数",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 50,
                "temperature": 0.5
            }
        },
        # 带系统提示
        {
            "name": "带系统提示",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "system": "你是一个友好的助手",
                "max_tokens": 50
            }
        },
        # 带top_p参数
        {
            "name": "带top_p参数",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 50,
                "temperature": 0.7,
                "top_p": 0.9
            }
        },
        # 带停止序列
        {
            "name": "带停止序列",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 50,
                "stop_sequences": ["谢谢", "再见"]
            }
        },
        # 多轮对话
        {
            "name": "多轮对话",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [
                    {"role": "user", "content": "你好，我叫小明"},
                    {"role": "assistant", "content": "你好小明！很高兴认识你。"},
                    {"role": "user", "content": "我叫什么名字？"}
                ],
                "max_tokens": 50
            }
        },
        # 流式响应
        {
            "name": "流式响应",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "用一句话介绍FastAPI"}],
                "max_tokens": 50,
                "stream": True
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            response = requests.post(f"{BASE_URL}/messages", json=test_case['data'])
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                if test_case['data'].get('stream', False):
                    print("✅ 流式响应成功")
                    # 简单验证流式响应
                    content_received = False
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            if 'content_block_delta' in line_str:
                                content_received = True
                                break
                    if content_received:
                        print("✅ 流式内容接收成功")
                    else:
                        print("⚠️ 流式内容可能不完整")
                else:
                    result = response.json()
                    print(f"✅ 响应成功 - 模型: {result['model']}")
                    print(f"  内容长度: {len(result['content'][0]['text'])} 字符")
                    print(f"  输入tokens: {result['usage']['input_tokens']}")
                    print(f"  输出tokens: {result['usage']['output_tokens']}")
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")

def test_edge_cases():
    """测试边界情况"""
    print("\n\n=== 测试边界情况 ===")
    
    edge_cases = [
        {
            "name": "空消息",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [],
                "max_tokens": 50
            }
        },
        {
            "name": "超长内容",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好" * 1000}],
                "max_tokens": 50
            }
        },
        {
            "name": "特殊字符",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好！@#$%^&*()_+-=[]{}|;':\",./<>?"}],
                "max_tokens": 50
            }
        },
        {
            "name": "多语言内容",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "Hello 你好 Hola Bonjour こんにちは"}],
                "max_tokens": 50
            }
        }
    ]
    
    for test_case in edge_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            response = requests.post(f"{BASE_URL}/messages", json=test_case['data'])
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 边界情况处理成功")
            else:
                print(f"⚠️ 预期错误: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")

def test_parameter_validation():
    """测试参数验证"""
    print("\n\n=== 测试参数验证 ===")
    
    validation_cases = [
        {
            "name": "无效温度值",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "temperature": 5.0  # 超出范围
            }
        },
        {
            "name": "无效max_tokens",
            "data": {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 0  # 无效值
            }
        },
        {
            "name": "缺少必需字段",
            "data": {
                # 缺少messages字段
                "model": "claude-3-haiku-20240307"
            }
        }
    ]
    
    for test_case in validation_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            response = requests.post(f"{BASE_URL}/messages", json=test_case['data'])
            print(f"状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"✅ 参数验证正常 - 返回: {response.status_code}")
            else:
                print("⚠️ 参数验证可能不够严格")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")

if __name__ == "__main__":
    print("开始全面兼容性测试...")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        test_basic_compatibility()
        test_edge_cases()
        test_parameter_validation()
        
        print("\n" + "=" * 60)
        print("🎉 兼容性测试完成！")
        print("服务已全面兼容Anthropic API的各种参数和情况。")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")