from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
import json
import time
import uuid
import logging
from typing import Dict, Any, Union
from config import settings
from models import AnthropicRequest, AnthropicResponse
from converter import ProtocolConverter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-gateway")

app = FastAPI(title="LLM API Gateway", description="OpenAI和Anthropic API协议转换网关")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "LLM API Gateway 运行中", "version": "1.0.0"}


@app.post("/v1/messages")
async def anthropic_switch(request: AnthropicRequest):
    """将Anthropic协议请求转换为OpenAI协议并调用配置的服务"""

    logger.info("=" * 60)
    logger.info("【请求】Anthropic API")
    logger.info(f"Model: {request.model}")
    logger.info(f"Messages count: {len(request.messages)}")
    for i, msg in enumerate(request.messages):
        content = msg.content
        if isinstance(content, list):
            content_preview = str(content)[:200]
        else:
            content_preview = content[:200] if len(str(content)) > 200 else content
        logger.info(f"  Message {i} [{msg.role}]: {content_preview}")
    if request.system:
        system_preview = request.system[:200] if isinstance(request.system, str) else str(request.system)[:200]
        logger.info(f"  System: {system_preview}")
    logger.info(f"  Max tokens: {request.max_tokens}")
    logger.info(f"  Temperature: {request.temperature}")
    logger.info(f"  Stream: {request.stream}")
    logger.info("=" * 60)

    # 转换为OpenAI请求格式
    openai_request = ProtocolConverter.anthropic_to_openai(request, settings.openai_model)

    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.openai_api_key}"
    }

    # 处理流式响应
    if request.stream:
        return StreamingResponse(
            stream_anthropic_response(openai_request, headers),
            media_type="text/event-stream"
        )

    # 非流式响应处理
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers=headers,
                json=openai_request.dict(exclude_none=True)
            )

            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"调用OpenAI服务失败: {error_detail}"
                )

            # 解析OpenAI响应
            openai_response_data = response.json()

            # 记录OpenAI原始响应日志
            logger.info("【响应】OpenAI 原始响应")
            if "choices" in openai_response_data and len(openai_response_data["choices"]) > 0:
                content = openai_response_data["choices"][0].get("message", {}).get("content", "")
                content_preview = content[:500] if len(content) > 500 else content
                logger.info(f"  Content: {content_preview}")
            if "usage" in openai_response_data:
                logger.info(f"  Usage: {openai_response_data['usage']}")
            logger.info("=" * 60)

            from models import OpenAIResponse
            openai_response = OpenAIResponse(**openai_response_data)

            # 转换回Anthropic格式
            anthropic_response = ProtocolConverter.openai_to_anthropic(openai_response)

            # 记录转换后的Anthropic响应日志
            logger.info("【响应】Anthropic 转换响应")
            if anthropic_response.content:
                text_content = ""
                for block in anthropic_response.content:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")
                content_preview = text_content[:500] if len(text_content) > 500 else text_content
                logger.info(f"  Content: {content_preview}")
            logger.info(f"  Stop reason: {anthropic_response.stop_reason}")
            logger.info(f"  Usage: {anthropic_response.usage}")
            logger.info("=" * 60)

            return anthropic_response

        except httpx.RequestError as e:
            logger.error(f"【错误】网络错误: {str(e)}")
            raise HTTPException(status_code=503, detail=f"网络错误: {str(e)}")
        except Exception as e:
            logger.error(f"【错误】服务器内部错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


async def stream_anthropic_response(openai_request, headers):
    """处理流式响应"""
    logger.info("【流式响应】开始流式响应...")
    logger.info(f"  请求URL: {settings.openai_base_url}/chat/completions")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 发送流式请求
            async with client.stream(
                "POST",
                f"{settings.openai_base_url}/chat/completions",
                headers=headers,
                json=openai_request.dict(exclude_none=True)
            ) as response:

                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'error': f'调用服务失败: {error_text.decode()}', 'status': response.status_code})}\n\n"
                    return

                # 生成Anthropic格式的流式响应ID
                message_id = f"msg_{uuid.uuid4().hex}"

                # 发送开始事件
                start_event = {
                    "type": "message_start",
                    "message": {
                        "id": message_id,
                        "type": "message",
                        "role": "assistant",
                        "model": settings.openai_model,
                        "content": [],
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0}
                    }
                }
                yield f"data: {json.dumps(start_event)}\n\n"

                # 发送内容块事件
                content_block_event = {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""}
                }
                yield f"data: {json.dumps(content_block_event)}\n\n"

                # 处理流式响应
                logger.info("【流式响应】开始接收数据...")
                full_content = ""
                chunk_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    full_content += content
                                    chunk_count += 1
                                    if chunk_count % 10 == 0:
                                        logger.info(f"  [Chunk {chunk_count}] 累计内容长度: {len(full_content)}")

                                    # 发送内容增量事件
                                    delta_event = {
                                        "type": "content_block_delta",
                                        "index": 0,
                                        "delta": {"type": "text_delta", "text": content}
                                    }
                                    yield f"data: {json.dumps(delta_event)}\n\n"
                        except json.JSONDecodeError:
                            continue

                # 发送内容块结束事件
                end_event = {
                    "type": "content_block_stop",
                    "index": 0
                }
                yield f"data: {json.dumps(end_event)}\n\n"

                # 发送消息结束事件
                message_stop_event = {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": "end_turn",
                        "stop_sequence": None
                    },
                    "usage": {"output_tokens": len(full_content)}
                }
                yield f"data: {json.dumps(message_stop_event)}\n\n"

                # 发送最终结束事件
                final_event = {"type": "message_stop"}
                yield f"data: {json.dumps(final_event)}\n\n"

                # 记录流式响应完成日志
                logger.info("【流式响应】完成")
                content_preview = full_content[:300] if len(full_content) > 300 else full_content
                logger.info(f"  总内容长度: {len(full_content)} 字符")
                logger.info(f"  内容预览: {content_preview}...")
                logger.info("=" * 60)

        except Exception as e:
            logger.error(f"【流式响应错误】{str(e)}")
            error_event = {"type": "error", "error": {"type": "api_error", "message": str(e)}}
            yield f"data: {json.dumps(error_event)}\n\n"


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )