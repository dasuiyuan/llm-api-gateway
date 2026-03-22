import json
import uuid
from typing import List, Dict, Any, Union, Tuple
from models import (
    AnthropicRequest, AnthropicResponse, AnthropicMessage,
    OpenAIRequest, OpenAIResponse, OpenAIMessage, OpenAITool,
    OpenAIToolCall, OpenAIToolCallFunction
)


class ThinkingParser:
    """
    将模型输出的 <think>...</think> 标签流式解析为
    ("thinking", content) / ("text", content) 片段序列。
    支持跨 chunk 的标签边界。
    """

    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    def __init__(self):
        self.buffer = ""
        self.in_thinking = False

    def feed(self, chunk: str) -> List[Tuple[str, str]]:
        """消费一段新内容，返回已确定的 (type, content) 片段列表"""
        self.buffer += chunk
        results = []

        while True:
            if not self.in_thinking:
                idx = self.buffer.find(self.OPEN_TAG)
                if idx == -1:
                    # 保留末尾可能是不完整标签的部分
                    safe_len = max(0, len(self.buffer) - len(self.OPEN_TAG) + 1)
                    if safe_len > 0:
                        results.append(("text", self.buffer[:safe_len]))
                        self.buffer = self.buffer[safe_len:]
                    break
                else:
                    if idx > 0:
                        results.append(("text", self.buffer[:idx]))
                    self.buffer = self.buffer[idx + len(self.OPEN_TAG):]
                    self.in_thinking = True
            else:
                idx = self.buffer.find(self.CLOSE_TAG)
                if idx == -1:
                    safe_len = max(0, len(self.buffer) - len(self.CLOSE_TAG) + 1)
                    if safe_len > 0:
                        results.append(("thinking", self.buffer[:safe_len]))
                        self.buffer = self.buffer[safe_len:]
                    break
                else:
                    if idx > 0:
                        results.append(("thinking", self.buffer[:idx]))
                    self.buffer = self.buffer[idx + len(self.CLOSE_TAG):]
                    self.in_thinking = False

        return results

    def flush(self) -> List[Tuple[str, str]]:
        """流结束时冲刷剩余 buffer"""
        if not self.buffer:
            return []
        seg_type = "thinking" if self.in_thinking else "text"
        result = [(seg_type, self.buffer)]
        self.buffer = ""
        return result


class ProtocolConverter:
    """协议转换器：在Anthropic和OpenAI格式之间进行转换"""

    @staticmethod
    def anthropic_to_openai(anthropic_req: AnthropicRequest, target_model: str) -> OpenAIRequest:
        """将Anthropic请求转换为OpenAI请求"""

        messages = []

        # 系统消息
        if anthropic_req.system:
            system_content = anthropic_req.system
            if isinstance(system_content, list):
                text_content = ""
                for block in system_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
                system_content = text_content
            messages.append(OpenAIMessage(role="system", content=system_content))

        # 转换消息列表
        for msg in anthropic_req.messages:
            content = msg.content

            # 纯字符串直接转
            if isinstance(content, str):
                messages.append(OpenAIMessage(role=msg.role, content=content))
                continue

            # content 是列表，需要区分 tool_use / tool_result / text
            if msg.role == "assistant":
                messages.extend(ProtocolConverter._convert_assistant_message(content))
            elif msg.role == "user":
                messages.extend(ProtocolConverter._convert_user_message(content))

        # 转换工具定义
        openai_tools = None
        if anthropic_req.tools:
            openai_tools = []
            for tool in anthropic_req.tools:
                if isinstance(tool, dict):
                    openai_tools.append(OpenAITool(
                        type="function",
                        function={
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "parameters": tool.get("input_schema", {})
                        }
                    ))

        # 转换 tool_choice
        openai_tool_choice = None
        if anthropic_req.tool_choice:
            tc = anthropic_req.tool_choice
            if isinstance(tc, dict):
                tc_type = tc.get("type", "auto")
                if tc_type == "auto":
                    openai_tool_choice = "auto"
                elif tc_type == "any":
                    openai_tool_choice = "required"
                elif tc_type == "tool":
                    openai_tool_choice = {"type": "function", "function": {"name": tc.get("name", "")}}
            elif isinstance(tc, str):
                openai_tool_choice = tc

        openai_request = OpenAIRequest(
            model=target_model,
            messages=messages,
            max_tokens=anthropic_req.max_tokens,
            temperature=anthropic_req.temperature,
            stream=anthropic_req.stream,
            tools=openai_tools,
            tool_choice=openai_tool_choice
        )

        if anthropic_req.top_p is not None:
            openai_request.top_p = anthropic_req.top_p
        if anthropic_req.stop_sequences is not None:
            openai_request.stop = anthropic_req.stop_sequences

        return openai_request

    @staticmethod
    def _convert_assistant_message(content: List[Dict[str, Any]]) -> List[OpenAIMessage]:
        """将包含 tool_use 块的 assistant 消息转为 OpenAI 格式"""
        text_parts = []
        tool_calls = []

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(OpenAIToolCall(
                    id=block.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                    type="function",
                    function=OpenAIToolCallFunction(
                        name=block.get("name", ""),
                        arguments=json.dumps(block.get("input", {}))
                    )
                ))

        text_content = "".join(text_parts) if text_parts else None
        return [OpenAIMessage(
            role="assistant",
            content=text_content,
            tool_calls=tool_calls if tool_calls else None
        )]

    @staticmethod
    def _convert_user_message(content: List[Dict[str, Any]]) -> List[OpenAIMessage]:
        """将包含 tool_result 块的 user 消息转为 OpenAI 格式（tool role messages）"""
        messages = []
        text_parts = []

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_result":
                result_content = block.get("content", "")
                # content 可能是字符串或内容块列表
                if isinstance(result_content, list):
                    text = ""
                    for c in result_content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text += c.get("text", "")
                    result_content = text
                messages.append(OpenAIMessage(
                    role="tool",
                    tool_call_id=block.get("tool_use_id", ""),
                    content=str(result_content) if result_content is not None else ""
                ))

        # tool result 消息放在前面，再放文本（如有）
        if text_parts:
            messages.append(OpenAIMessage(role="user", content="".join(text_parts)))

        return messages

    @staticmethod
    def openai_to_anthropic(openai_resp: OpenAIResponse, request_id: str = None) -> AnthropicResponse:
        """将OpenAI响应转换为Anthropic响应"""

        if request_id is None:
            request_id = f"msg_{uuid.uuid4().hex}"

        choice = openai_resp.choices[0]
        message = choice.message
        content = []

        # 文本内容（解析 <think>...</think> 标签）
        if message.content:
            parser = ThinkingParser()
            segments = parser.feed(message.content) + parser.flush()
            for seg_type, seg_content in segments:
                if not seg_content:
                    continue
                if seg_type == "thinking":
                    content.append({"type": "thinking", "thinking": seg_content})
                else:
                    content.append({"type": "text", "text": seg_content})

        # 工具调用
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    input_data = json.loads(tc.function.arguments or "{}")
                except (json.JSONDecodeError, AttributeError):
                    input_data = {}
                content.append({
                    "type": "tool_use",
                    "id": tc.id or f"toolu_{uuid.uuid4().hex[:8]}",
                    "name": tc.function.name or "" if tc.function else "",
                    "input": input_data
                })

        # finish_reason → stop_reason
        finish_reason = choice.finish_reason
        if finish_reason == "stop":
            stop_reason = "end_turn"
        elif finish_reason == "length":
            stop_reason = "max_tokens"
        elif finish_reason == "tool_calls":
            stop_reason = "tool_use"
        else:
            stop_reason = None

        return AnthropicResponse(
            id=request_id,
            type="message",
            role="assistant",
            content=content,
            model=openai_resp.model,
            stop_reason=stop_reason,
            stop_sequence=None,
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
