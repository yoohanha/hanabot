#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[Stage-0] Ollama 연결 테스트

학생이 다음 명령으로 직접 실행 가능:
  python hanabot/test_ollama.py
"""

import os
import sys
import json
import urllib.request
import time
from pathlib import Path

# Windows UTF-8 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_env():
    """환경변수 로드"""
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

def main():
    """메인"""
    load_env()

    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    chat_model = os.getenv('CHAT_MODEL', 'llama3.1')

    print("🔗 Ollama 테스트")
    print(f"   주소: {ollama_host}")
    print(f"   모델: {chat_model}\n")

    try:
        # 요청 데이터
        prompt = "짧게 답변해: 안녕"
        data = {
            'model': chat_model,
            'prompt': prompt,
            'stream': False,
            'temperature': 0.7
        }

        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            f"{ollama_host}/api/generate",
            data=req_data,
            headers={'Content-Type': 'application/json'}
        )

        print("⏳ Ollama 응답 대기 중...")
        start_time = time.time()

        response = urllib.request.urlopen(req, timeout=60)
        result = json.loads(response.read().decode('utf-8'))

        elapsed = time.time() - start_time

        print(f"✅ 응답 받았습니다! ({elapsed:.1f}초)\n")
        print("Ollama의 응답:")
        print("-" * 60)
        print(result['response'].strip())
        print("-" * 60)

    except urllib.error.URLError as e:
        print(f"❌ 오류: Ollama 서버에 연결할 수 없습니다")
        print(f"   {ollama_host}에 접속할 수 없습니다")
        print(f"   Ollama가 실행 중인지 확인하세요: ollama serve")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
