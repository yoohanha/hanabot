#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하나봇 실행 프로그램

학생들이 더블클릭으로 실행하는 메인 진입점
"""

import os
import sys
import subprocess
from pathlib import Path

# Windows UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_env():
    """간단하게 .env 파일 읽기"""
    env_vars = {}
    env_path = Path('.env')

    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                        os.environ[key.strip()] = value.strip()

    return env_vars

def check_environment():
    """환경 점검"""
    print("=" * 60)
    print("🔍 환경 점검 중...\n")

    issues = []

    # 1. Python 버전
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"✓ Python {python_version} 설치됨")

    # 2. .env 파일 확인
    if not Path('.env').exists():
        issues.append({
            'msg': "❌ .env 파일이 없습니다",
            'solution': [
                "💡 해결 방법:",
                "  1. 파일 탐색기에서 .env.example을 찾으세요",
                "  2. 복사해서 .env 로 이름을 바꾸세요",
                "  또는 아래 명령으로 자동 생성:",
                "  > copy .env.example .env"
            ]
        })
    else:
        print("✓ .env 파일 확인됨")
        env_vars = load_env()

        # 3. .env의 설정 확인
        ollama_host = env_vars.get('OLLAMA_HOST')
        chat_model = env_vars.get('CHAT_MODEL')
        embed_model = env_vars.get('EMBED_MODEL')

        if ollama_host:
            print(f"✓ Ollama 주소: {ollama_host}")
        else:
            issues.append({
                'msg': "❌ .env에 OLLAMA_HOST가 설정되지 않았습니다",
                'solution': [
                    "💡 해결 방법:",
                    "  .env 파일을 열어서 다음 줄을 추가하세요:",
                    "  OLLAMA_HOST=http://localhost:11434"
                ]
            })

        if chat_model:
            print(f"✓ 채팅 모델: {chat_model}")
        else:
            issues.append({
                'msg': "❌ .env에 CHAT_MODEL이 설정되지 않았습니다",
                'solution': [
                    "💡 해결 방법:",
                    "  .env 파일을 열어서 다음 줄을 추가하세요:",
                    "  CHAT_MODEL=llama3.1"
                ]
            })

        if embed_model:
            print(f"✓ 임베딩 모델: {embed_model}")
        else:
            issues.append({
                'msg': "❌ .env에 EMBED_MODEL이 설정되지 않았습니다",
                'solution': [
                    "💡 해결 방법:",
                    "  .env 파일을 열어서 다음 줄을 추가하세요:",
                    "  EMBED_MODEL=bge-m3"
                ]
            })

    # 4. Ollama 연결 테스트
    try:
        import urllib.request
        import json

        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        try:
            response = urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=2)
            data = json.loads(response.read().decode('utf-8'))
            print(f"✓ Ollama 서버 연결 성공 ({ollama_host})")
        except Exception as e:
            issues.append({
                'msg': f"❌ Ollama 서버에 연결할 수 없습니다",
                'solution': [
                    "💡 해결 방법:",
                    "  1. Ollama가 설치되어 있는지 확인하세요",
                    "  2. Ollama를 시작하세요: ollama serve",
                    f"  3. 주소가 맞는지 확인하세요: {ollama_host}"
                ]
            })
    except Exception as e:
        issues.append({
            'msg': f"❌ 네트워크 오류: {str(e)}",
            'solution': ["💡 Ollama 서버 연결을 확인하세요"]
        })

    # 5. 모델 설치 확인
    if os.getenv('OLLAMA_HOST') and os.getenv('CHAT_MODEL'):
        try:
            import urllib.request
            import json

            ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            chat_model = os.getenv('CHAT_MODEL')

            response = urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=2)
            data = json.loads(response.read().decode('utf-8'))
            models = [m['name'] for m in data.get('models', [])]

            if not any(chat_model in m for m in models):
                issues.append({
                    'msg': f"❌ 모델 '{chat_model}'이 Ollama에 설치되지 않았습니다",
                    'solution': [
                        "💡 해결 방법:",
                        f"  터미널에서 다음 명령을 실행하세요:",
                        f"  > ollama pull {chat_model}"
                    ]
                })
            else:
                print(f"✓ 모델 '{chat_model}' 설치됨")
        except Exception:
            pass

    print()

    if issues:
        print("=" * 60)
        print("⚠️  문제가 있습니다:\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue['msg']}")
            for line in issue['solution']:
                print(f"   {line}")
            print()

        print("=" * 60)
        return False

    print("=" * 60)
    print("✅ 환경 확인 완료! 모든 설정이 정상입니다.\n")
    return True

def show_menu():
    """메뉴 표시"""
    print("=" * 60)
    print("📋 메뉴\n")
    print("1. 설치 확인 (안녕)")
    print("2. 하나봇과 대화 (RAG 없음)")
    print("3. 하나봇에게 질문 (RAG)")
    print("4. RAG 있음/없음 비교")
    print("5. 파인튜닝 비교 (4가지)")
    print("6. 품질 점수 보기 (RAGAS · 5문항)")
    print("7. 하나 AI 학원 홈페이지 열기")
    print("8. AI 에이전트 · 도구 연결 (4-1)")
    print("9. AI 에이전트 · 메모리 (4-2)")
    print("10. AI 에이전트 · MCP 도구 (4-3)")
    print("11. AI 에이전트 · 안전장치 (4-4)")
    print("q. 종료\n")
    print("-" * 60)
    return input("번호를 입력하세요 (1-11, q) > ").strip()

def run_hello_test():
    """Ollama 연결 테스트"""
    command = "python hanabot/test_ollama.py"
    print(f"\n▶ 실행하는 명령: {command}\n")

    try:
        result = subprocess.run(
            [sys.executable, "hanabot/test_ollama.py"],
            cwd=Path.cwd(),
            capture_output=False,
            text=True
        )
        print()
    except Exception as e:
        print(f"❌ 오류: {str(e)}\n")

def run_command(script_path, name, args=None):
    """명령 실행"""
    if not Path(script_path).exists():
        print(f"❌ 오류: {script_path} 파일을 찾을 수 없습니다\n")
        return

    cmd_args = [sys.executable, script_path]
    if args:
        cmd_args.extend(args)

    command = f"python {script_path}" + (f" {' '.join(args)}" if args else "")
    print(f"\n▶ 실행하는 명령: {command}\n")

    try:
        result = subprocess.run(
            cmd_args,
            cwd=Path.cwd(),
            capture_output=False,
            text=True
        )
        print()
    except Exception as e:
        print(f"❌ 오류: {str(e)}\n")

def check_model_exists(model_name):
    """Ollama 모델 존재 확인"""
    try:
        import urllib.request
        import json

        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        response = urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=2)
        data = json.loads(response.read().decode('utf-8'))
        models = [m['name'] for m in data.get('models', [])]

        return any(model_name in m for m in models)
    except:
        return False

def main():
    """메인 프로그램"""
    print("\n")
    print("🤖 " + "=" * 56)
    print("   하나봇 (HanaBot) - 사내 규정 Q&A 챗봇")
    print("   " + "=" * 56)
    print()

    # 환경 점검
    if not check_environment():
        print("⚠️  환경 설정을 완료한 후 다시 실행하세요.")
        input("엔터를 눌러 종료하세요...")
        sys.exit(1)

    # 메인 루프
    while True:
        choice = show_menu()

        if choice == '1':
            run_hello_test()
        elif choice == '2':
            run_command("apps/chat_no_rag.py", "RAG 없음 대화")
        elif choice == '3':
            run_command("apps/chat_with_rag.py", "RAG 대화")
        elif choice == '4':
            run_command("apps/compare.py", "RAG 비교")
        elif choice == '5':
            # 파인튜닝 모델 체크
            if check_model_exists('hanabot-ft'):
                run_command("labs/1-3/compare_ft.py", "파인튜닝 비교")
            else:
                print("\n⚠️  hanabot-ft 모델이 없습니다.")
                print("💡 사용 방법:")
                print("   1. Google Colab에서 finetune_colab.ipynb 실행")
                print("   2. hanabot_finetuned.zip 다운로드")
                print("   3. models/hanabot-ft/ 에 압축 해제")
                print("   4. python labs/1-3/make_modelfile.py 실행")
                print("   그 후 메뉴 5번을 다시 선택하세요.\n")
        elif choice == '6':
            run_command("labs/1-4/eval_ragas.py", "품질 점수 (RAGAS)", args=["--n", "5"])
        elif choice == '7':
            # [2부] 하나 AI 학원 홈페이지
            run_command("web/server.py", "하나 AI 학원 홈페이지")
        elif choice == '8':
            # [4-1] AI 에이전트 도구 연결
            run_command("labs/4-1/hana_tools.py", "AI 에이전트 · 도구 연결")
        elif choice == '9':
            # [4-2] AI 에이전트 메모리
            run_command("labs/4-2/long_memory.py", "AI 에이전트 · 메모리")
        elif choice == '10':
            # [4-3] AI 에이전트 MCP 도구
            run_command("labs/4-3/hanabot_mcp.py", "AI 에이전트 · MCP 도구")
        elif choice == '11':
            # [4-4] AI 에이전트 안전장치
            run_command("labs/4-4/interactive_with_guard.py", "AI 에이전트 · 안전장치")
        elif choice.lower() == 'q':
            print("프로그램을 종료합니다. 👋\n")
            break
        else:
            print("❌ 잘못된 선택입니다. 1-11 또는 q를 입력하세요.\n")

if __name__ == "__main__":
    main()
