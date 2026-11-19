# 하나봇 프로젝트 규칙

이 문서는 Claude Code가 이 프로젝트에서 따를 지침입니다.

## 👥 대상 독자
파이썬 초보 학생. 코드는 **짧고 읽기 쉽게**.

## 💬 언어
- **주석**: 한국어 (코드 설명)
- **화면 메시지**: 한국어 (사용자와 소통)
- **.bat 파일**: 영어만 (한글 지원 안 함, 안내는 파이썬에서 출력)

## 🔖 단계 표시
새로 추가하거나 변경한 코드에는 단계 주석을 단다:
```python
# [1-2] Chroma로 벡터 DB 교체
# [2-3] Agent 로직 추가
```

## 🏗️ 폴더 구조 (섞지 않음)
```
hanabot/               # 본체 패키지
apps/                  # 실행 파일 (CLI, API 등)
labs/<단계>/           # 단계별 연습 코드
data/                  # 문서, 샘플 데이터
```

## 🔐 모델 & 설정
**원칙**: 코드에 모델 이름, 주소, 경로를 쓰지 말 것. 모두 `.env`에서 읽음.

- **채팅 모델**: `llama3.1` (로컬 Ollama)
- **임베딩 모델**: `bge-m3` (로컬 Ollama)
- **설정 읽기**: `hanabot/config.py` → `.env`
- **외부 API 금지**: 사내 문서를 외부로 보내지 않음

### 예시 (.env)
```
OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=llama3.1
EMBED_MODEL=bge-m3
```

### 예시 (config.py)
```python
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
```

## ✅ 단계 완료 절차
1. **직접 실행해서 확인**: `python apps/<파일>.py` 등으로 작동 검증
2. **README 한 줄**: "1-2: RAG 구현 완료 (Chroma 통합)" 같이 간단히 기록
3. **커밋 & 태그**:
   ```bash
   git add .
   git commit -m "[1-2] RAG 기본 구조 구현"
   git tag stage-1-2
   ```

## 🖥️ Windows 환경
- `.bat` 파일 이름, 내용은 **영어로만** 작성
- 한글 안내/설명은 `print()`, 로깅 등 **파이썬 코드에서만** 출력
- 예: `run.bat` (내용: `@echo off` 등)

## 🔐 1-4 LLMOps 가이드

**원칙**: 1-4 실습에서는 기록(로그)만 Langfuse Cloud로 보낸다.
- 모델: 로컬 Ollama 그대로 (변경 없음)
- 가상 학원 데이터라 허용
- 실제 회사: Langfuse를 사내 서버에 설치

## 🌐 2부 웹 규칙 (Part 2: 홈페이지 껍데기)

### 폴더 격리 원칙
- **2부 파일 위치**: `web/` 폴더 **안에만**
  - 프론트엔드: `web/static/` (HTML, CSS, JS)
  - 백엔드: `web/server.py` (Flask/FastAPI)
  - 자산: `web/static/assets/` (이미지, 폰트 등)

### 1부 보호 (수정 금지)
- `hanabot/` - 1부 본체 패키지 (수정 금지)
- `labs/` - 1부 연습 코드 (수정 금지)
- `apps/` - 기존 1부 앱 (수정 금지)
- `data/RAG_PLAN.md` - 읽기만 허용

### 외부 접점 (변경 허용 범위)
- `run.py` - 2부 메뉴 한 줄 추가만
- `README.md` - 2부 설명 한 줄 추가만

### 이미지 & 자산 관리
- **준비된 이미지**: `images/` → `web/static/assets/`로 옮겨 사용
- **새로운 자산**: `web/static/assets/`에만 추가

## 🔗 3-1 연결 규칙 (Part 3: 채팅창과 RAG 연결)

### 수정 범위
- **수정 가능**: `web/` 폴더 **안에만** (`web/server.py`, `web/static/`)
- **수정 금지**: `hanabot/`, `labs/`, `apps/` (1-2부 코드는 그대로)
- **불러오기만**: `from hanabot.rag import ...` 등으로 1부 모듈 가져다 쓰기

### 단계 표시
- 새로 추가하거나 수정한 코드: `# [3-1]` 주석 필수

## 🌐 3부 웹 완성 규칙 (Part 3: 웹 기능 완성)

### 신청 데이터 저장
- **위치**: `web/data/*.json` (DB 사용 금지)
- **파일**: `web/data/consultations.json` (상담신청), `web/data/enrollments.json` (수강신청)
- **형식**: 배열 `[{학번, 이메일, ...}, ...]`

### 개인정보 정책
- **받는 정보**: 학번(가상: HANA-001) · 이메일 · 선호사항만
- **받지 않음**: 이름, 전화번호, 주민번호 (보안/프라이버시)

## 📌 체크리스트
단계를 마치기 전에 확인:
- [ ] 코드에 모델/주소 하드코딩 없음
- [ ] 주석과 메시지는 한국어
- [ ] 새 코드에 단계 표시 있음
- [ ] 직접 실행해서 작동 확인
- [ ] README 갱신 & 커밋 & 태그
