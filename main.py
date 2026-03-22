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
    async with httpx.AsyncClient(timeout=300.0) as client:
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
    """处理流式响应，支持 text 和 tool_use"""
    logger.info("【流式响应】开始流式响应...")
    logger.info(f"  请求URL: {settings.openai_base_url}/chat/completions")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
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

                message_id = f"msg_{uuid.uuid4().hex}"

                # message_start
                yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'model': settings.openai_model, 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"

                # 追踪状态
                text_block_index = None   # 文本块在 content 中的下标
                next_block_index = 0
                # tool_call_blocks: openai_index -> {block_index, id, name, args}
                tool_call_blocks: Dict[int, Dict] = {}
                full_text = ""
                finish_reason = "stop"

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if not data.get("choices"):
                        continue

                    choice = data["choices"][0]
                    delta = choice.get("delta", {})

                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

                    # —— 文本 delta ——
                    text_chunk = delta.get("content")
                    if text_chunk:
                        if text_block_index is None:
                            text_block_index = next_block_index
                            next_block_index += 1
                            yield f"data: {json.dumps({'type': 'content_block_start', 'index': text_block_index, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                        full_text += text_chunk
                        yield f"data: {json.dumps({'type': 'content_block_delta', 'index': text_block_index, 'delta': {'type': 'text_delta', 'text': text_chunk}})}\n\n"

                    # —— tool call delta ——
                    for tc in (delta.get("tool_calls") or []):
                        tc_idx = tc.get("index", 0)

                        if tc_idx not in tool_call_blocks:
                            # 第一次出现，开启新的 tool_use 块
                            tc_id = tc.get("id", f"toolu_{uuid.uuid4().hex[:8]}")
                            tc_name = (tc.get("function") or {}).get("name", "")
                            block_index = next_block_index
                            next_block_index += 1
                            tool_call_blocks[tc_idx] = {
                                "block_index": block_index,
                                "id": tc_id,
                                "name": tc_name,
                                "args": ""
                            }
                            yield f"data: {json.dumps({'type': 'content_block_start', 'index': block_index, 'content_block': {'type': 'tool_use', 'id': tc_id, 'name': tc_name, 'input': {}}})}\n\n"

                        args_chunk = (tc.get("function") or {}).get("arguments", "")
                        if args_chunk:
                            tool_call_blocks[tc_idx]["args"] += args_chunk
                            block_index = tool_call_blocks[tc_idx]["block_index"]
                            yield f"data: {json.dumps({'type': 'content_block_delta', 'index': block_index, 'delta': {'type': 'input_json_delta', 'partial_json': args_chunk}})}\n\n"

                # 关闭所有 content_block
                if text_block_index is not None:
                    yield f"data: {json.dumps({'type': 'content_block_stop', 'index': text_block_index})}\n\n"
                for tc_data in tool_call_blocks.values():
                    yield f"data: {json.dumps({'type': 'content_block_stop', 'index': tc_data['block_index']})}\n\n"

                # stop_reason
                if finish_reason == "tool_calls":
                    stop_reason = "tool_use"
                elif finish_reason == "length":
                    stop_reason = "max_tokens"
                else:
                    stop_reason = "end_turn"

                yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': {'output_tokens': len(full_text)}})}\n\n"
                yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

                logger.info("【流式响应】完成")
                logger.info(f"  文本长度: {len(full_text)} 字符, tool calls: {len(tool_call_blocks)}")
                logger.info("=" * 60)

        except Exception as e:
            logger.error(f"【流式响应错误】{str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': str(e)}})}\n\n"


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