# [1-3] Modelfile 생성 및 Ollama 등록
import sys
import os
import glob
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from hanabot.config import OLLAMA_BASE_URL
from dotenv import load_dotenv

# .env 로드
load_dotenv()
COMPANY_NAME = os.getenv("COMPANY_NAME", "하나 AI 학원")

# GGUF 파일 찾기
model_dir = Path(__file__).parent.parent.parent / "models" / "hanabot-ft"
model_dir.mkdir(parents=True, exist_ok=True)

gguf_files = list(model_dir.glob("*.gguf"))

if not gguf_files:
    print("❌ GGUF 파일을 찾을 수 없습니다.")
    print(f"경로: {model_dir}")
    print("다음 단계:")
    print("1. Colab에서 hanabot_finetuned.zip 다운로드")
    print("2. 압축 해제")
    print("3. hanabot_finetuned.gguf를 models/hanabot-ft/ 에 옮기기")
    sys.exit(1)

gguf_file = gguf_files[0]
print(f"✓ GGUF 파일 찾음: {gguf_file.name}")
print(f"  크기: {gguf_file.stat().st_size / 1e9:.2f}GB")

# Modelfile 로드 (Colab에서 받은 것)
colab_modelfile = model_dir / "Modelfile"
if colab_modelfile.exists():
    with open(colab_modelfile, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"✓ Colab Modelfile 로드됨")
    # TEMPLATE 추출
    if "TEMPLATE" in content:
        template = [line for line in content.split("\n") if "TEMPLATE" in line][0]
    else:
        template = None
else:
    print("⚠️  Colab Modelfile이 없습니다. 기본값 사용")
    template = None

# 새 Modelfile 생성
system_prompt = f"{COMPANY_NAME}의 도우미 하나봇입니다. 학원 규정에 대한 질문에 답합니다."

modelfile = f"""FROM {gguf_file.name}

PARAMETER temperature 0.7
PARAMETER top_p 0.9

SYSTEM {system_prompt}"""

if template:
    modelfile += f"\n\n{template}"

# Modelfile 저장
modelfile_path = model_dir / "Modelfile"
with open(modelfile_path, "w", encoding="utf-8") as f:
    f.write(modelfile)

print(f"✓ Modelfile 생성 완료")
print()
print("=" * 80)
print("생성된 Modelfile:")
print("=" * 80)
print(modelfile)
print()

# Ollama 등록
print("=" * 80)
print("Ollama 등록 (ollama create hanabot-ft)")
print("=" * 80)
print()

import subprocess

# 모델 등록
cmd = f'ollama create hanabot-ft -f "{modelfile_path}"'
print(f"실행: {cmd}")
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.returncode == 0:
    print("✓ 모델 등록 완료")
else:
    print(f"❌ 오류: {result.stderr}")
    sys.exit(1)

print()

# ollama list 확인
print("=" * 80)
print("ollama list 확인")
print("=" * 80)
print()

cmd = "ollama list"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)

# hanabot-ft 찾기
if "hanabot-ft" in result.stdout:
    print("✓ hanabot-ft 모델이 등록되었습니다")
else:
    print("⚠️  hanabot-ft 모델을 찾을 수 없습니다")
