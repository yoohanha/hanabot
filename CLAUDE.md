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
**원칙**: 단계 표시 주석은 `.py` · `.js` 에만. 마크다운 파일에는 `<!-- [3-1] -->` 형태 주석으로 대체.

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

## 🤖 4부 AI 에이전트 규칙 (Part 4: AI 에이전트)

### 파일 위치
- **새 파일**: `labs/4-1/` 폴더 **안에만** 생성
- **도구 저장 경로**: `labs/4-1/data/` (도구가 생성하는 파일)

### 수정 범위
- **수정 금지**: `hanabot/`, `apps/`, `web/` (1-3부 코드 그대로)
- **불러오기만**: `from hanabot.rag import ...` 등으로 1-3부 모듈 가져다 쓰기

### 단계 표시
- 새로 추가하거나 수정한 코드: `# [4-1]` 주석 필수

### 모델 & 도구 설정
- **채팅 모델**: `.env`의 `CHAT_MODEL` (기본: `llama3.1`)
- **외부 API 금지**: 사내 데이터는 로컬만 사용
- **도구 (Tool)**: 에이전트가 호출할 함수/스크립트는 `labs/4-1/` 내에서만 작성

### 4-2: 에이전트와 메모리
#### 파일 위치
- **새 파일**: `labs/4-2/` 폴더 **안에만** 생성
- **메모리 저장**: `labs/4-2/memory/` (사용자별 메모리 JSON)

#### 단계 표시
- 새로 추가하거나 수정한 코드: `# [4-2]` 주석 필수

#### 도구 재사용
- **금지**: 4-1 도구를 복사하기
- **필수**: `from labs.4_1.hana_tools import get_today, search_rules, ...` 로 import해서 사용

#### 메모리 정책 (개인정보 보호)
- **저장 허용**: 학번 (예: HANA-001), 선호사항 (관심 과정, 선호 시간)
- **저장 금지**: 이름, 전화번호, 주민번호, 이메일 (보안/프라이버시)
- **형식**: `{"student_id": "HANA-001", "preferences": {...}, "created_at": "..."}`

### 4-3: MCP 도구 연결
#### 파일 위치
- **새 파일**: `labs/4-3/` 폴더 **안에만** 생성
- **도구 호출 로그**: `labs/4-3/data/` (MCP 도구 실행 결과)

#### 단계 표시
- 새로 추가하거나 수정한 코드: `# [4-3]` 주석 필수

#### MCP 서버 정책
- **허용**: 내 PC에서 도는 로컬 MCP 서버만 사용
- **금지**: 외부 서버로 데이터를 보내는 MCP 서버 사용 금지 (보안/프라이버시)

#### Filesystem MCP 사용 규칙
- **접근 범위**: `data/` 폴더만 읽기 가능
- **허용 도구**: 읽기 도구만 (`read_file`, `list_directory` 등)
- **금지**: 쓰기/삭제 도구 사용 금지

#### 도구 재사용 (1~2교시)
- **금지**: 4-1, 4-2 도구를 복사하기
- **필수**: `from labs.4_1.hana_tools import ...`, `from labs.4_2.long_memory import ...` 로 import해서 사용

### 4-4: 안전장치 평가
#### 파일 위치
- **새 파일**: `labs/4-4/` 폴더 **안에만** 생성
- **테스트 데이터**: `labs/4-4/data/` (공격 테스트 결과)

#### 단계 표시
- 새로 추가하거나 수정한 코드: `# [4-4]` 주석 필수

#### 테스트 범위 제한
- **허용**: `labs/4-1/data/`의 실습 예약 파일에만 공격 테스트 적용
- **금지**: `web/data/` 절대 금지 (실제 사용자 데이터 보호)

#### 도구 재사용 (1~3교시)
- **금지**: 4-1, 4-2, 4-3 도구를 복사하기
- **필수**: `from labs.4_1.hana_tools import ...`, `from labs.4_2.long_memory import ...`, `from labs.4_3.mcp_integration import ...` 로 import해서 감싸기

#### 사용자 승인
- **승인 채널**: 터미널(CLI)에서만 `y/n` 입력 받기
- **금지**: 외부 메신저(이메일, Slack, etc.)로 승인 요청 절대 금지
- **예**: `input("위험한 동작을 수행하시겠습니까? (y/n): ")`

## 📊 5부 LangGraph 규칙 (Part 5: 에이전틱 AI)

### 파일 위치
- **새 파일**: `labs/5-1/` ~ `labs/5-6/` 폴더 **안에만** 생성
- **데이터 저장**: `labs/5-N/data/` (에이전트 로그, 상태 파일)

### 단계 표시
- 새로 추가하거나 수정한 코드: `# [5-N]` 주석 필수 (N: 1~6)

### 수정 범위
- **수정 금지**: `hanabot/`, `apps/`, `labs/1-4/` (1~4부 코드 그대로)
- **불러오기만**: `from hanabot.rag import ...`, `from labs.4_1.hana_tools import ...` 등으로 1~4부 모듈 가져다 쓰기
- **web/ 수정**: 5-5에서만 (`web/server.py`, `web/static/`) · 예약 파일은 `labs/4-1/data/` 만

### 모델 & 도구 설정
- **LLM 설정**: `ChatOllama` 고정
  ```python
  ChatOllama(
      model=os.getenv("CHAT_MODEL", "llama3.1"),
      temperature=0,          # 에이전트 결정성 필요
      num_ctx=8192,          # 컨텍스트 윈도우
      num_predict=512,       # 최대 출력 토큰
      timeout=120            # 타임아웃 120초
  )
  ```
- **시스템 메시지**: 오늘 날짜 `{today}` 포함 필수
- **테스트**: 가짜 테스트 금지 · 실제 실행 결과만 기록

### 도구 재사용 (1~4부)
- **금지**: 도구를 복사하기
- **필수**: import로 가져와 사용
  ```python
  from labs.4_1.hana_tools import get_today, search_rules, ...
  from labs.4_2.long_memory import load_memory, save_memory, ...
  from labs.4_3.mcp_integration import run_mcp_tool, ...
  from labs.4_4.guard_check import check_safety, ...
  ```

### 5-5: Human in the Loop 웹 연결
#### 파일 위치
- **새 파일**: `labs/5-5/` 폴더 **안에만** 생성
- **웹 수정**: `web/server.py`, `web/static/` **안에만** (범위 제한)

#### 웹 수정 범위
- **허용**: 엔드포인트 추가만 (`/accept`, `/reject` 등)
- **금지**: 기존 RAG 채팅 로직 수정 금지 (1-3부 기능 유지)
- **예약 저장**: `labs/4-1/data/` 에만 사용 (`web/data/` 금지)
- **개인정보**: 학번, 선호사항만 (3부 정책 그대로)

#### 단계 표시
- 새로 추가하거나 수정한 코드: `# [5-5]` 주석 필수

#### 도구 재사용 (1~4부)
- **금지**: 도구를 복사하기
- **필수**: import로 가져와 사용
  ```python
  from labs.4_1.hana_tools import get_today, search_rules, ...
  from labs.4_2.long_memory import load_memory, save_memory, ...
  from labs.4_3.mcp_integration import run_mcp_tool, ...
  from labs.4_4.guard_check import check_safety, ...
  ```

## 📌 체크리스트
단계를 마치기 전에 확인:
- [ ] 코드에 모델/주소 하드코딩 없음
- [ ] 주석과 메시지는 한국어
- [ ] 새 코드에 단계 표시 있음
- [ ] 직접 실행해서 작동 확인
- [ ] README 갱신 & 커밋 & 태그
