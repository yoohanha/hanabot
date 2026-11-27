#!/bin/bash
# [5-7] AWS GPU 서버 초기화 스크립트 (Ubuntu 에서 자동 실행)

set -e

# [5-7] 로그 파일 경로 설정
LOG_FILE="/var/log/hanabot-setup.log"

# [5-7] 로그 출력 함수
log_msg() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_msg "=== 하나봇 GPU 서버 초기화 시작 ==="

# [5-7] 패키지 업데이트
log_msg "1단계: 시스템 패키지 업데이트"
apt-get update
apt-get upgrade -y

# [5-7] Git 설치
log_msg "2단계: Git 설치"
apt-get install -y git curl wget

# [5-7] Docker & Docker Compose 설치
log_msg "3단계: Docker 설치"
apt-get install -y docker.io
systemctl start docker
systemctl enable docker

# [5-7] Docker Compose 설치 (최신 버전)
log_msg "4단계: Docker Compose 설치"
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# [5-7] Ollama 설치 (공식 스크립트)
log_msg "5단계: Ollama 설치"
curl -fsSL https://ollama.ai/install.sh | sh

# [5-7] Ollama 서비스 활성화 (백그라운드)
log_msg "6단계: Ollama 서비스 시작"
systemctl start ollama
systemctl enable ollama

# [5-7] OLLAMA_HOST 환경변수 설정 (0.0.0.0:11434 으로 외부 접근 가능)
log_msg "7단계: Ollama 환경설정"
mkdir -p /etc/environment.d
echo "OLLAMA_HOST=0.0.0.0:11434" | tee -a /etc/environment.d/ollama.conf

# [5-7] Ollama 서비스 재시작 (새 환경변수 적용)
systemctl restart ollama

# [5-7] Ollama 서버가 준비될 때까지 대기 (최대 5분)
log_msg "8단계: Ollama 서버 준비 대기"
ATTEMPT=0
MAX_ATTEMPTS=30
until curl -s http://localhost:11434/api/tags > /dev/null; do
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        log_msg "⚠️ Ollama 서버 시작 실패 (타임아웃)"
        break
    fi
    log_msg "  Ollama 준비 중... ($((ATTEMPT+1))/${MAX_ATTEMPTS})"
    sleep 10
    ((ATTEMPT++))
done

# [5-7] 모델 다운로드 (llama3.1 · bge-m3)
log_msg "9단계: 모델 다운로드 시작 (약 15-20분 소요)"
# [5-7] llama3.1 모델 풀
ollama pull llama3.1 2>&1 | tee -a "$LOG_FILE"
# [5-7] bge-m3 임베딩 모델 풀
ollama pull bge-m3 2>&1 | tee -a "$LOG_FILE"

log_msg "✅ 모델 다운로드 완료"

# [5-7] 홈 디렉토리로 이동
cd /home/ubuntu

# [5-7] 하나봇 저장소 복제 (main 브랜치)
log_msg "10단계: 하나봇 프로젝트 클론"
git clone https://github.com/yoohanha/hanabot.git
cd hanabot

# [5-7] .env 파일 생성 (AWS 서버 환경변수)
log_msg "11단계: .env 파일 생성"
cat > .env << 'EOF'
# [5-7] AWS GPU 서버용 환경변수
OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=llama3.1
EMBED_MODEL=bge-m3
WEB_HOST=0.0.0.0
WEB_PORT=8080
EOF

log_msg "✅ .env 파일 생성 완료"

# [5-7] .env 파일 권한 제한 (보안)
chmod 600 .env

# [5-7] Python 의존성 설치
log_msg "12단계: Python 의존성 설치"
apt-get install -y python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --quiet

# [5-7] Docker 이미지 빌드 (이미지가 없을 경우)
log_msg "13단계: Docker 이미지 빌드"
docker build -t hanabot:5-6 . 2>&1 | tee -a "$LOG_FILE"

# [5-7] docker-compose.aws.yml 로 하나봇 웹 서버 시작
log_msg "14단계: Docker Compose 로 웹 서버 시작"
docker-compose -f docker-compose.aws.yml up -d

# [5-7] 초기화 완료 메시지
log_msg "=== 🎉 하나봇 GPU 서버 초기화 완료 ==="
log_msg "✅ Ollama 서버: http://localhost:11434"
log_msg "✅ 하나봇 웹: http://localhost:8080"
log_msg "📝 로그 확인: tail -f $LOG_FILE"
