# [5-6] 하나봇 Docker 이미지
# Python 3.12-slim + requirements.txt 설치
# Ollama는 호스트 PC 것 사용: http://host.docker.internal:11434

FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 (C/C++ 헤더 필요할 수 있음)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 복사
COPY . .

# 환경 변수 설정 (기본값)
ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=8080
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV CHAT_MODEL=llama3.1
ENV EMBED_MODEL=bge-m3
ENV LLM_BACKEND=ollama

# 웹 서버 실행
CMD ["python", "web/server.py"]
