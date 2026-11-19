# 🤖 하나봇 (HanaBot)

사내 규정 Q&A 챗봇을 11단계에 걸쳐 차근차근 만드는 **대학 수업 프로젝트**.

LangChain, RAG, Fine-tuning, LLMOps부터 Docker, CI/CD, Kubernetes까지 최신 AI 서비스 개발 전체 과정을 배웁니다.

---

## 📁 폴더 구조

```
hanabot/
├── PLAN.md                # 11단계 로드맵
├── README.md              # 이 파일
├── CLAUDE.md              # 개발 규칙
├── .env                   # 환경변수 (git 제외)
├── .env.example           # 환경변수 템플릿
├── requirements.txt       # Python 의존성
│
├── hanabot/               # 📦 본체 패키지
│   ├── config.py          # .env에서 설정 로드
│   ├── llm.py             # LLM 연결 (Ollama)
│   ├── embeddings.py      # 임베딩 모델
│   ├── rag/               # RAG 핵심 로직
│   └── agent/             # AI Agent 로직
│
├── apps/                  # 🚀 실행 파일
│   ├── cli.py             # 커맨드라인 인터페이스
│   ├── api.py             # FastAPI 서버
│   └── run.py             # 단계별 실행 메뉴
│
├── web/                   # 🌐 웹 인터페이스 (2부부터)
│   ├── static/            # HTML, CSS, JavaScript
│   ├── server.py          # 웹 서버
│   └── assets/            # 이미지, 폰트 등
│
├── labs/                  # 📝 단계별 연습 코드
│   ├── 1-1-langchain/     # LangChain 기초
│   ├── 1-2-rag/           # RAG 프로토타입
│   ├── 1-3-finetuning/    # Fine-tuning 실험
│   ├── 1-4-llmops/        # LLMOps 연습
│   ├── 2-1-rag-service/   # RAG 서비스화
│   ├── 2-2-langgraph/     # LangGraph 워크플로우
│   ├── 2-3-ai-agent/      # AI Agent 고급
│   ├── 2-4-vllm/          # vLLM 최적화
│   ├── 2-5-docker/        # Docker 컨테이너화
│   ├── 2-6-cicd/          # CI/CD 파이프라인
│   └── 2-7-k8s/           # Kubernetes 배포
│
├── data/                  # 📚 문서 & 자료
│   ├── docs/              # 마크다운 문서
│   ├── sample_regulations/ # 샘플 사내 규정
│   └── embeddings/        # 벡터 DB (git 제외)
│
├── docker/                # 🐳 Docker 설정 (2-5부터)
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── k8s/                   # ☸️  Kubernetes 설정 (2-7부터)
│   ├── deployment.yaml
│   └── service.yaml
│
└── .github/workflows/     # ⚙️ CI/CD (2-6부터)
    └── ci.yml
```

---

## 🚀 시작하기

### 1️⃣ 사전 준비
```bash
# Ollama 설치 및 모델 다운로드
ollama pull llama3.1
ollama pull bge-m3
ollama serve
```

### 2️⃣ 환경 설정
```bash
# .env 파일 생성 (템플릿 기반)
cp .env.example .env
```

`.env` 내용:
```env
OLLAMA_HOST=http://localhost:11434
CHAT_MODEL=llama3.1
EMBED_MODEL=bge-m3
```

### 3️⃣ Python 환경
```bash
# 가상환경 생성
python -m venv .venv

# 활성화 (Windows)
.venv\Scripts\activate

# 활성화 (macOS/Linux)
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 4️⃣ 첫 실행

**콘솔에서 실행:**
```bash
# 메뉴식 실행 (추천)
python run.py
# → 메뉴 1번: 환경 확인 (인사말 테스트)
# → 메뉴 7번: 웹 홈페이지 열기
```

**웹 기반 실행:**
```bash
# Windows: web 폴더 아래 webrun.bat 더블클릭
# 또는 콘솔에서:
python web/server.py
# → http://localhost:8080 접속
```

---

## 📍 단계 이동 방법

### 특정 단계로 이동
```bash
# 예: Stage 1-2로 이동
git checkout stage-1-2

# 현재 브랜치와 태그 확인
git branch -v
git tag -l
```

### 단계별 변경 내역
각 단계를 시작하기 전에 커밋 로그 확인:
```bash
git log --oneline --graph
```

---

## 📋 단계별 변경 내역

| 단계 | 커밋 메시지 | 주요 추가 | 실행 방법 |
|------|-----------|---------|---------|
| **stage-0** | [Stage-0] 프로젝트 초기 설정 | CLAUDE.md, .gitignore, PLAN.md, README.md | - |
| **stage-1-1** | [1-1] LangChain 기초 | hanabot/llm.py, apps/cli.py | `python apps/cli.py` |
| **stage-1-2** | [1-2] RAG 구현 완료 (RAG_PLAN.md 기반) | hanabot/rag.py, apps/chat*.py, apps/compare.py | `apps/run.bat` |
| **stage-1-3** | [1-3] 파인튜닝 완료 (말투 FT + 지식 RAG) | labs/1-3/compare_ft.py, models/hanabot-ft/ | `apps/run.bat` |
| **stage-1-3** | [1-3] Fine-tuning | labs/1-3-finetuning/, 평가 데이터셋 | `python labs/1-3-finetuning/train.py` |
| **stage-1-4** | [1-4] LLMOps 완료 (추적 Langfuse · 평가 RAGAS · 프롬프트 버전 관리) | hanabot/rag.py (Langfuse 추적), eval_ragas.py (평가), push_prompt.py (버전 관리) | `python labs/1-4/eval_ragas.py --compare --n 5` |
| **stage-2-web** | [2부] 하나 AI 학원 홈페이지 껍데기 | web/, FastAPI, RAG_PLAN.md 연결, 하나봇 자리 | `python run.py` → 7번 |
| **stage-3-1** | [3-1] 홈페이지 하나봇 RAG 연결 | web/server.py, web/static/script.js, 근거 표시, 스레드 처리 | `webrun.bat` |
| **stage-3-2** | [3교시] 홈페이지 완성 (상담 · GPU 예약 · 수강 신청 · API 정리) | web/services.py, web/server.py, web/static/page.html, web/API.md, web/check_api.py | `python web/check_api.py` |
| **stage-2-1** | [2-1] RAG 서비스 | apps/api.py, FastAPI, 웹 UI | `python apps/api.py` |
| **stage-2-2** | [2-2] LangGraph | hanabot/agent/workflow.py | `python apps/cli.py --agent` |
| **stage-2-3** | [2-3] AI Agent | hanabot/agent/tools.py | `python apps/cli.py --agent-advanced` |
| **stage-2-4** | [2-4] vLLM | labs/2-4-vllm/, 배치 최적화 | `python labs/2-4-vllm/server.py` |
| **stage-2-5** | [2-5] Docker | docker/Dockerfile, docker-compose.yml | `docker-compose up` |
| **stage-2-6** | [2-6] CI/CD | .github/workflows/ci.yml | (자동 실행) |
| **stage-2-7** | [2-7] Kubernetes | k8s/deployment.yaml | `kubectl apply -f k8s/` |

---

## 💡 개발 규칙

[CLAUDE.md](CLAUDE.md)를 참고하세요.

- 주석과 메시지는 **한국어**
- 모델 설정은 **.env에서 읽음** (코드에 하드코딩 없음)
- 각 단계 완료 후: 실행 확인 → README 갱신 → 커밋 + 태그

---

## 🔗 추가 자료

- [로드맵 상세](PLAN.md)
- [개발 규칙](CLAUDE.md)

---

**행운을 빕니다!** 🚀
