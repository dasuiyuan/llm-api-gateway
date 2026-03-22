from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

# Anthropic请求格式 - 完整支持
class AnthropicMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]  # 支持文本或内容块列表

class AnthropicRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=819200)
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    stream: Optional[bool] = False
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

# Anthropic工具调用相关
class AnthropicTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]

class AnthropicToolChoice(BaseModel):
    type: str = "auto"  # "auto", "any", "tool"
    name: Optional[str] = None

# OpenAI请求格式 - 完整支持
class OpenAIMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]  # 支持文本或内容块列表

class OpenAITool(BaseModel):
    type: str = "function"
    function: Dict[str, Any]

class OpenAIRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    max_tokens: Optional[int] = Field(default=1000, ge=1)
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    tools: Optional[List[OpenAITool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    user: Optional[str] = None

# Anthropic响应格式 - 完整支持
class AnthropicResponse(BaseModel):
    id: str
    type: str
    role: str
    content: List[Dict[str, Any]]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

# Anthropic流式响应事件
class AnthropicStreamEvent(BaseModel):
    type: str
    # 根据事件类型动态包含其他字段

# OpenAI响应格式 - 完整支持
class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIMessage
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage
    system_fingerprint: Optional[str] = None