# 使用 Python 3.9 作为基础镜像
FROM python:3.9-slim
# FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY main.py .
COPY ocr.py .
COPY download_models.py .

# 创建模型目录
RUN mkdir -p models/EasyOCR

# 复制本地模型文件（如果有）
COPY models/EasyOCR /app/models/EasyOCR

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 如果没有本地模型，则下载
RUN if [ ! -d "/app/models/EasyOCR" ]; then python download_models.py; fi

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]  