import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # OpenAI兼容服务配置
    openai_base_url: str = "https://modelservice.jdcloud.com/v1"
    openai_api_key: str = "pk-3a990a97-436f-4bf3-a71b-a5e09d5c57d6"
    openai_model: str = "MiniMax-M2.5"
    
    # 应用配置
    api_host: str = "0.0.0.0"
    api_port: int = 3038
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()