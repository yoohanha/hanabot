#!/bin/bash
# [5-7] AWS GPU 서버 초기화 스크립트 (Ubuntu 에서 자동 실행)

# [5-7] 로그 파일 경로 설정
LOG_FILE="/var/log/hanabot-setup.log"

# [5-7] 로그 출력 함수
log_msg() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# [5-7] 에러 처리 함수
error_exit() {
    log_msg "❌ 오류: $1"
    exit 1
}

log_msg "=== 하나봇 GPU 서버 초기화 시작 ==="

# [5-7] 패키지 업데이트
log_msg "1단계: 시스템 패키지 업데이트"
apt-get update || error_exit "패키지 업데이트 실패"
apt-get upgrade -y || error_exit "패키지 업그레이드 실패"

# [5-7] Git 설치
log_msg "2단계: Git 설치"
apt-get install -y git curl wget || error_exit "Git 설치 실패"

# [5-7] Docker 설치 확인 · 필요 시 설치
log_msg "3단계: Docker 설치 (필요 시)"
if command -v docker &> /dev/null; then
    log_msg "  Docker 이미 설치됨"
else
    log_msg "  Docker 설치 중..."
    curl -fsSL https://get.docker.com | sh || error_exit "Docker 설치 실패"
fi
systemctl start docker || error_exit "Docker 시작 실패"
systemctl enable docker || error_exit "Docker 자동시작 활성화 실패"

# [5-7] Docker Compose 플러그인 확인
log_msg "4단계: Docker Compose 플러그인 확인"
if docker compose version &> /dev/null; then
    log_msg "  Docker Compose 플러그인 이미 설치됨"
else
    error_exit "Docker Compose 플러그인 없음 (Docker 20.10+ 필요)"
fi

# [5-7] Ollama 설치 (공식 스크립트)
log_msg "5단계: Ollama 설치"
curl -fsSL https://ollama.ai/install.sh | sh || error_exit "Ollama 설치 실패"

# [5-7] Ollama 서비스 활성화 (백그라운드)
log_msg "6단계: Ollama 서비스 시작"
systemctl start ollama || error_exit "Ollama 시작 실패"
systemctl enable ollama

# [5-7] Ollama systemd override 설정 (OLLAMA_HOST 환경변수)
log_msg "7단계: Ollama 환경설정 (systemd override)"
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
# [5-7] Ollama 호스트 설정 (외부 접근 가능)
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

# [5-7] systemd 설정 재로드 & Ollama 재시작
systemctl daemon-reload || error_exit "systemd daemon-reload 실패"
systemctl restart ollama || error_exit "Ollama 재시작 실패"

# [5-7] Ollama 서버가 준비될 때까지 대기 (최대 5분)
log_msg "8단계: Ollama 서버 준비 대기"
ATTEMPT=0
MAX_ATTEMPTS=30
until curl -s http://localhost:11434/api/tags > /dev/null; do
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        log_msg "[경고] Ollama 서버 시작 실패 (타임아웃)"
        break
    fi
    log_msg "  Ollama 준비 중... ($((ATTEMPT+1))/${MAX_ATTEMPTS})"
    sleep 10
    ATTEMPT=$((ATTEMPT+1))
done

# [5-7] 홈 디렉토리로 이동
cd /home/ubuntu || error_exit "홈 디렉토리 이동 실패"

# [5-7] 하나봇 저장소 복제 (main 브랜치)
log_msg "9단계: 하나봇 프로젝트 클론"
git clone https://github.com/yoohanha/hanabot.git || error_exit "저장소 클론 실패"
cd hanabot || error_exit "프로젝트 디렉토리 이동 실패"

# [5-7] .env 파일 생성 (AWS 서버 환경변수)
log_msg "10단계: .env 파일 생성"
cat > .env << 'EOF'
# [5-7] AWS GPU 서버용 환경변수
OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=llama3.1
EMBED_MODEL=bge-m3
WEB_HOST=0.0.0.0
WEB_PORT=8080
LLM_BACKEND=ollama
EOF

log_msg "✅ .env 파일 생성 완료"

# [5-7] .env 파일 권한 제한 (보안)
chmod 600 .env

# [5-7] .env 에서 모델 이름 읽기
source .env
log_msg "11단계: 모델 다운로드 시작 (약 15-20분 소요)"

# [5-7] 채팅 모델 풀
log_msg "  다운로드 중: $CHAT_MODEL"
ollama pull "$CHAT_MODEL" 2>&1 | tee -a "$LOG_FILE" || error_exit "모델 $CHAT_MODEL 다운로드 실패"

# [5-7] 임베딩 모델 풀
log_msg "  다운로드 중: $EMBED_MODEL"
ollama pull "$EMBED_MODEL" 2>&1 | tee -a "$LOG_FILE" || error_exit "모델 $EMBED_MODEL 다운로드 실패"

log_msg "✅ 모델 다운로드 완료"

# [5-7] Docker Compose 로 하나봇 웹 서버 시작 (aws.yml 오버라이드)
log_msg "12단계: Docker Compose 로 웹 서버 시작"
docker compose -f docker-compose.yml -f labs/5-7/aws/docker-compose.aws.yml up -d --build 2>&1 | tee -a "$LOG_FILE" || error_exit "Docker Compose 시작 실패"

# [5-7] 초기화 완료 메시지
log_msg "=== [완료] 하나봇 GPU 서버 초기화 완료 ==="
log_msg "✅ Ollama 서버: http://localhost:11434"
log_msg "✅ 하나봇 웹: http://localhost:8080"
log_msg "[로그 확인] tail -f $LOG_FILE"
