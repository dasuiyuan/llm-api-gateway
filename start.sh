#!/bin/bash

# 激活conda环境
source $(conda info --base)/etc/profile.d/conda.sh
conda activate llm-api-gateway

# 启动FastAPI服务
echo "启动LLM API Gateway服务..."
echo "服务将在 http://localhost:8000 启动"
echo "按 Ctrl+C 停止服务"

python main.py