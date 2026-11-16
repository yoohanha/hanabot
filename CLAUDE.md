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

## 📌 체크리스트
단계를 마치기 전에 확인:
- [ ] 코드에 모델/주소 하드코딩 없음
- [ ] 주석과 메시지는 한국어
- [ ] 새 코드에 단계 표시 있음
- [ ] 직접 실행해서 작동 확인
- [ ] README 갱신 & 커밋 & 태그
