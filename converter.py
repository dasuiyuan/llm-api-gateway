import uuid
from typing import List, Dict, Any, Union
from models import (
    AnthropicRequest, AnthropicResponse, AnthropicMessage,
    OpenAIRequest, OpenAIResponse, OpenAIMessage
)

class ProtocolConverter:
    """协议转换器：在Anthropic和OpenAI格式之间进行转换"""
    
    @staticmethod
    def anthropic_to_openai(anthropic_req: AnthropicRequest, target_model: str) -> OpenAIRequest:
        """将Anthropic请求转换为OpenAI请求"""
        
        # 处理系统消息
        messages = []
        
        # 如果有系统消息，添加到消息列表开头
        if anthropic_req.system:
            system_content = anthropic_req.system
            # 处理复杂的system格式（数组或字符串）
            if isinstance(system_content, list):
                # 如果是内容块列表，提取文本内容
                text_content = ""
                for block in system_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
                system_content = text_content
            messages.append(OpenAIMessage(role="system", content=system_content))
        
        # 转换用户消息和助手消息
        for msg in anthropic_req.messages:
            # 处理content可能是字符串或列表的情况
            content = msg.content
            if isinstance(content, list):
                # 如果是内容块列表，提取文本内容
                text_content = ""
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
                content = text_content
            messages.append(OpenAIMessage(role=msg.role, content=content))
        
        # 构建OpenAI请求，支持更多参数
        openai_request = OpenAIRequest(
            model=target_model,
            messages=messages,
            max_tokens=anthropic_req.max_tokens,
            temperature=anthropic_req.temperature,
            stream=anthropic_req.stream
        )
        
        # 映射其他可选参数
        if anthropic_req.top_p is not None:
            openai_request.top_p = anthropic_req.top_p
        if anthropic_req.stop_sequences is not None:
            openai_request.stop = anthropic_req.stop_sequences
        
        return openai_request
    
    @staticmethod
    def openai_to_anthropic(openai_resp: OpenAIResponse, request_id: str = None) -> AnthropicResponse:
        """将OpenAI响应转换为Anthropic响应"""
        
        if request_id is None:
            request_id = f"msg_{uuid.uuid4().hex}"
        
        # Anthropic的内容格式是列表，包含text类型的字典
        content = [{"type": "text", "text": openai_resp.choices[0].message.content}]
        
        # 转换finish_reason为stop_reason
        finish_reason = openai_resp.choices[0].finish_reason
        stop_reason = None
        stop_sequence = None
        
        if finish_reason == "stop":
            stop_reason = "end_turn"
        elif finish_reason == "length":
            stop_reason = "max_tokens"
        elif finish_reason == "tool_calls":
            stop_reason = "tool_use"
        
        return AnthropicResponse(
            id=request_id,
            type="message",
            role="assistant",
            content=content,
            model=openai_resp.model,
            stop_reason=stop_reason,
            stop_sequence=stop_sequence,
            usage={
                "input_tokens": openai_resp.usage.prompt_tokens,
                "output_tokens": openai_resp.usage.completion_tokens
            }
        )
    
    @staticmethod
    def convert_anthropic_content_to_string(content: Union[str, List[Dict[str, Any]]]) -> str:
        """将Anthropic内容转换为字符串"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)
        return ""