#!/usr/bin/env python3
# [2-1] 하나 AI 학원 웹 서버 (FastAPI)

import os
import json
import re
import socket
import webbrowser
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# .env 로드
load_dotenv()

# 설정
PORT = int(os.getenv('WEB_PORT', 8080))
HOST = os.getenv('WEB_HOST', 'localhost')
PROJECT_ROOT = Path(__file__).parent.parent
WEB_STATIC = PROJECT_ROOT / 'web' / 'static'
RAG_PLAN = PROJECT_ROOT / 'data' / 'RAG_PLAN.md'

# FastAPI 앱
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# [2-1] RAG_PLAN.md 파싱
def parse_rag_docs():
    """RAG_PLAN.md에서 RAG_DOCS 부분을 파싱해서 JSON으로 반환"""
    if not RAG_PLAN.exists():
        return {}

    with open(RAG_PLAN, 'r', encoding='utf-8') as f:
        content = f.read()

    # RAG_DOCS_START와 RAG_DOCS_END 사이 추출
    start_marker = '<!-- RAG_DOCS_START -->'
    end_marker = '<!-- RAG_DOCS_END -->'

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        return {}

    rag_content = content[start_idx + len(start_marker):end_idx]

    # # 제목, ## 소제목, 내용 파싱
    docs = {}
    current_title = None
    current_section = None
    current_text = []

    for line in rag_content.split('\n'):
        line = line.strip()

        if line.startswith('# ') and not line.startswith('## '):
            # 제목 (# 으로 시작, ## 아님)
            current_title = line[2:].strip()
            if current_title and current_title not in docs:
                docs[current_title] = {}
            current_section = None
            current_text = []

        elif line.startswith('## '):
            # 소제목
            if current_title:
                if current_section and current_text:
                    docs[current_title][current_section] = ' '.join(current_text).strip()

                current_section = line[3:].strip()
                current_text = []

        elif line and current_title and current_section:
            # 내용
            current_text.append(line)

    # 마지막 항목 저장
    if current_title and current_section and current_text:
        docs[current_title][current_section] = ' '.join(current_text).strip()

    return docs


# 캐시된 RAG 문서
_rag_docs_cache = None

def get_rag_docs():
    """RAG 문서 캐시 (매번 파일 읽지 않기 위해)"""
    global _rag_docs_cache
    _rag_docs_cache = parse_rag_docs()
    return _rag_docs_cache


# [2-1] API 엔드포인트
@app.get('/api/docs')
async def api_docs():
    """RAG_PLAN.md를 JSON으로 반환"""
    docs = get_rag_docs()
    return JSONResponse(docs)


@app.get('/api/docs/{title}')
async def api_docs_title(title: str):
    """특정 제목의 모든 소제목 반환"""
    docs = get_rag_docs()
    if title in docs:
        return JSONResponse({title: docs[title]})
    return JSONResponse({}, status_code=404)


@app.get('/api/docs/{title}/{section}')
async def api_docs_section(title: str, section: str):
    """특정 제목의 소제목 내용 반환"""
    docs = get_rag_docs()

    # URL 디코딩 (한글 처리)
    section = section.replace('%20', ' ')

    if title in docs and section in docs[title]:
        return JSONResponse({
            'title': title,
            'section': section,
            'content': docs[title][section]
        })
    return JSONResponse({}, status_code=404)


# [2-1] 채팅 엔드포인트 (3-1에서 hanabot/rag.py와 연결)
@app.post('/chat')
async def chat(request_body: dict):
    """사용자 메시지를 받고 응답 반환

    TODO: [3-1] hanabot/rag.py와 연결
    from hanabot.rag import rag_query
    reply = rag_query(message)
    """
    message = request_body.get('message', '')

    # 임시 응답 (3-1에서 실제 RAG 엔진으로 교체)
    reply = '하나봇은 3부에서 연결됩니다. 지금은 준비 중이에요.'

    return {'message': message, 'reply': reply}


# [2-1] 정적 파일 제공
@app.get('/')
async def root():
    """메인 페이지"""
    return FileResponse(WEB_STATIC / 'index.html')


@app.get('/page.html')
async def page():
    """메뉴 페이지"""
    return FileResponse(WEB_STATIC / 'page.html')


# 정적 파일 마운트
app.mount('/', StaticFiles(directory=WEB_STATIC, html=True), name='static')


# [2-1] 포트 사용 여부 확인
def is_port_in_use(host, port):
    """포트가 이미 사용 중인지 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


# 실행
if __name__ == '__main__':
    import uvicorn

    # 포트 확인
    if is_port_in_use(HOST, PORT):
        print(f'\n⚠️ 이미 켜져 있어요. 브라우저에서 바로 여세요')
        print(f'📍 http://{HOST}:{PORT}\n')
        exit(0)

    print(f'\n🤖 하나 AI 학원 홈페이지를 엽니다')
    print(f'📍 http://{HOST}:{PORT}')
    print(f'💡 끄려면 Ctrl + C\n')

    # 서버 시작 후 브라우저 열기 (별도 스레드에서)
    def open_browser():
        time.sleep(3)  # 서버 시작 대기
        try:
            webbrowser.open(f'http://{HOST}:{PORT}')
        except Exception as e:
            print(f'⚠️ 브라우저 열기 실패: {e}')

    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # 서버 실행
    uvicorn.run(app, host=HOST, port=PORT, log_level='critical')
