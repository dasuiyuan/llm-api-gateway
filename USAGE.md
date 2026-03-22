# 使用指南

## 项目概述

本项目是一个基于FastAPI的LLM API网关，实现了Anthropic和OpenAI协议之间的转换。它允许您使用Anthropic格式发送请求，但实际调用OpenAI兼容的服务，并将结果转换回Anthropic格式。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件，设置您的OpenAI兼容服务配置：

```bash
# OpenAI兼容服务配置
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-actual-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# 应用配置
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. 启动服务

```bash
python main.py
```

或使用uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务将在 http://localhost:8000 启动。

## API接口文档

### 健康检查

- **GET /** - 返回服务状态信息
- **GET /health** - 返回健康检查信息

### 协议转换接口

- **POST /anthropic/v1/messages** - 将Anthropic协议请求转换为OpenAI协议

#### 请求格式

```json
{
  "model": "claude-3-haiku-20240307",
  "messages": [
    {
      "role": "user",
      "content": "你好，请介绍一下FastAPI"
    }
  ],
  "max_tokens": 1000,
  "temperature": 0.7,
  "stream": false,
  "system": "你是一个有帮助的助手"
}
```

#### 响应格式

```json
{
  "id": "msg_123456789",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "FastAPI是一个现代、快速（高性能）的Web框架，用于基于标准Python类型提示构建API..."
    }
  ],
  "model": "gpt-3.5-turbo",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 15,
    "output_tokens": 200
  }
}
```

## 使用示例

### Python

```python
import requests

url = "http://localhost:8000/anthropic/v1/messages"

# 基础请求
data = {
    "model": "claude-3-haiku-20240307",
    "messages": [
        {
            "role": "user",
            "content": "你好，请介绍一下FastAPI"
        }
    ],
    "max_tokens": 1000
}

response = requests.post(url, json=data)
print(response.json())

# 带系统提示的请求
data_with_system = {
    "model": "claude-3-haiku-20240307",
    "messages": [
        {
            "role": "user",
            "content": "什么是RESTful API？"
        }
    ],
    "max_tokens": 500,
    "temperature": 0.5,
    "system": "你是一个专业的软件开发专家，请用简洁明了的语言回答技术问题。"
}

response = requests.post(url, json=data_with_system)
print(response.json())
```

### curl

```bash
# 基础请求
curl -X POST http://localhost:8000/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "你好，请介绍一下FastAPI"
      }
    ],
    "max_tokens": 1000
  }'

# 带系统提示的请求
curl -X POST http://localhost:8000/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "什么是RESTful API？"
      }
    ],
    "max_tokens": 500,
    "temperature": 0.5,
    "system": "你是一个专业的软件开发专家，请用简洁明了的语言回答技术问题。"
  }'
```

## 协议转换说明

### 请求转换

1. **Anthropic → OpenAI**
   - 将Anthropic的`messages`列表转换为OpenAI格式
   - 如果有`system`字段，将其作为第一条消息
   - 保持`max_tokens`、`temperature`等参数不变
   - 使用配置中指定的OpenAI模型

### 响应转换

1. **OpenAI → Anthropic**
   - 将OpenAI的响应内容包装在Anthropic的内容格式中
   - 转换`finish_reason`为Anthropic的`stop_reason`
   - 映射token使用量到Anthropic格式
   - 生成符合Anthropic格式的响应ID

## 错误处理

服务会返回适当的HTTP状态码和错误信息：

- **200**: 请求成功
- **400**: 请求参数错误
- **401**: API密钥无效
- **503**: 服务不可用（通常是OpenAI服务连接问题）
- **500**: 服务器内部错误

## 注意事项

1. 请确保在`.env`文件中配置有效的API密钥
2. 目前不支持流式响应（stream=true会被忽略）
3. 系统提示（system）是可选的，但推荐使用以获得更好的结果
4. 服务会自动处理内容格式的转换，无需额外配置

## 扩展功能

如果需要支持其他功能，可以：

1. 修改`models.py`添加新的字段支持
2. 更新`converter.py`中的转换逻辑
3. 在`main.py`中添加新的端点
4. 扩展环境变量配置

## 故障排除

### 连接被拒绝

确保服务已正确启动，并且端口8000未被占用。

### API密钥无效

检查`.env`文件中的`OPENAI_API_KEY`是否正确。

### 协议转换错误

检查请求和响应的JSON格式是否符合文档中的规范。