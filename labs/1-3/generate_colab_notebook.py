# [1-3] Google Colab 노트북 생성
import json
from pathlib import Path

# ipynb 구조
notebook = {
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

def add_markdown(text):
    notebook["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [text]
    })

def add_code(code):
    notebook["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [code]
    })

# 셀 작성
add_markdown("# 🤖 하나봇 파인튜닝 (Google Colab)\n\n"
            "Unsloth + Qwen2.5-3B-Instruct (4-bit)로 하나봇 모델을 파인튜닝합니다.")

add_markdown("## 1️⃣ GPU 확인")
add_code("import torch\nprint(f'GPU: {torch.cuda.get_device_name(0)}')\nprint(f'메모리: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB')")

add_markdown("## 2️⃣ Unsloth 설치 (3-5분 소요)")
add_code("!pip install unsloth[colab-new] -q\n"
        "!pip install datasets transformers bitsandbytes xformers -q\n"
        "print('✓ 설치 완료')")

add_markdown("## 3️⃣ 모델 로드 (Qwen2.5-3B-Instruct-bnb-4bit)")
add_code("from unsloth import FastLanguageModel\n\n"
        "model, tokenizer = FastLanguageModel.from_pretrained(\n"
        "    model_name='unsloth/Qwen2.5-3B-Instruct-bnb-4bit',\n"
        "    max_seq_length=2048,\n"
        "    dtype=None,\n"
        "    load_in_4bit=True,\n"
        ")\nprint('✓ 모델 로드 완료')")

add_markdown("## 4️⃣ LoRA 설정 (r=16, lora_alpha=16)")
add_code("model = FastLanguageModel.get_peft_model(\n"
        "    model,\n"
        "    r=16,\n"
        "    lora_alpha=16,\n"
        "    lora_dropout=0.05,\n"
        "    bias='none',\n"
        "    use_gradient_checkpointing=True,\n"
        "    use_rslora=True,\n"
        ")\nprint('✓ LoRA 적용 완료')")

add_markdown("## 5️⃣ 학습 데이터 업로드")
add_code("from google.colab import files\n\n"
        "print('hanabot_train.jsonl 파일을 선택해주세요')\n"
        "uploaded = files.upload()\n"
        "train_file = list(uploaded.keys())[0]\n"
        "print(f'✓ 업로드됨: {train_file}')")

add_markdown("## 6️⃣ 데이터 로드 및 형식 확인")
add_code("import json\nfrom datasets import Dataset\n\n"
        "# 데이터 로드\n"
        "data = []\n"
        "with open(train_file, 'r', encoding='utf-8') as f:\n"
        "    for line in f:\n"
        "        data.append(json.loads(line))\n\n"
        "# 형식 확인\n"
        "print(f'총 {len(data)}개 데이터')\n"
        "print(f'예시: {data[0]}')\n\n"
        "# Dataset 변환\n"
        "dataset = Dataset.from_dict({\n"
        "    'text': [str(item['conversations']) for item in data]\n"
        "})")

add_markdown("## 7️⃣ 학습 설정")
add_code("from transformers import TrainingArguments, Trainer\n\n"
        "training_args = TrainingArguments(\n"
        "    per_device_train_batch_size=4,\n"
        "    gradient_accumulation_steps=4,\n"
        "    warmup_steps=10,\n"
        "    num_train_epochs=2,\n"
        "    learning_rate=2e-4,\n"
        "    logging_steps=10,\n"
        "    save_steps=50,\n"
        "    output_dir='outputs',\n"
        "    optim='paged_adamw_8bit',\n"
        "    seed=42,\n"
        ")\nprint('✓ 학습 파라미터 설정 완료')")

add_markdown("## 8️⃣ 학습 실행 (20-30분 소요)")
add_code("from trl import SFTTrainer\n\n"
        "trainer = SFTTrainer(\n"
        "    model=model,\n"
        "    tokenizer=tokenizer,\n"
        "    args=training_args,\n"
        "    train_dataset=dataset,\n"
        "    dataset_text_field='text',\n"
        "    max_seq_length=2048,\n"
        ")\n\n"
        "trainer.train()\n"
        "print('✓ 학습 완료')")

add_markdown("## 9️⃣ Loss 그래프 (학습 과정 시각화)")
add_code("import matplotlib.pyplot as plt\nimport json\n\n"
        "# 학습 로그에서 loss 추출\n"
        "log_file = 'outputs/trainer_state.json'\n"
        "with open(log_file) as f:\n"
        "    logs = json.load(f)\n\n"
        "steps = [l['step'] for l in logs['log_history'] if 'loss' in l]\n"
        "losses = [l['loss'] for l in logs['log_history'] if 'loss' in l]\n\n"
        "plt.figure(figsize=(10, 5))\n"
        "plt.plot(steps, losses, marker='o')\n"
        "plt.xlabel('Step')\n"
        "plt.ylabel('Loss')\n"
        "plt.title('Learning Curve')\n"
        "plt.grid()\n"
        "plt.show()")

add_markdown("## 🔟 평가 (학습 전후 비교)")
add_code("# 평가 데이터 업로드\n"
        "print('hanabot_eval.jsonl 파일을 선택해주세요')\n"
        "uploaded = files.upload()\n"
        "eval_file = list(uploaded.keys())[0]\n\n"
        "# 평가 샘플 추출\n"
        "eval_data = []\n"
        "with open(eval_file, 'r', encoding='utf-8') as f:\n"
        "    for i, line in enumerate(f):\n"
        "        if i < 3:  # 처음 3개만\n"
        "            eval_data.append(json.loads(line))\n\n"
        "print(f'평가 샘플: {len(eval_data)}개')\n"
        "for i, item in enumerate(eval_data, 1):\n"
        "    q = item['conversations'][0]['content']\n"
        "    a = item['conversations'][1]['content']\n"
        "    print(f'\\n[샘플 {i}] Q: {q}')\n"
        "    print(f'정답: {a[:100]}...')")

add_markdown("## 1️⃣1️⃣ 모델 내보내기 (GGUF q4_k_m)")
add_code("from unsloth import unsloth_to_gguf\n\n"
        "unsloth_to_gguf(\n"
        "    model,\n"
        "    tokenizer,\n"
        "    quantization_method='q4_k_m',\n"
        "    output_filename='hanabot_finetuned.gguf',\n"
        ")\nprint('✓ GGUF 변환 완료')")

add_markdown("## 1️⃣2️⃣ Modelfile 생성 (Ollama 호환)")
add_code("modelfile = '''FROM ./hanabot_finetuned.gguf\n"
        "PARAMETER temperature 0.7\n"
        "PARAMETER top_p 0.9\n"
        "SYSTEM \\\"당신은 하나 AI 학원의 도우미 하나봇입니다. 학원 규정에 대한 질문에 답합니다.\\\"'''\n\n"
        "with open('Modelfile', 'w') as f:\n"
        "    f.write(modelfile)\n\n"
        "print('✓ Modelfile 생성 완료')")

add_markdown("## 1️⃣3️⃣ 파일 압축 & 다운로드")
add_code("import zipfile\nimport os\n\n"
        "# zip 파일 생성\n"
        "with zipfile.ZipFile('hanabot_finetuned.zip', 'w') as z:\n"
        "    z.write('hanabot_finetuned.gguf')\n"
        "    z.write('Modelfile')\n\n"
        "print(f'압축 크기: {os.path.getsize(\"hanabot_finetuned.zip\") / 1e9:.1f}GB')\n"
        "print('✓ hanabot_finetuned.zip 준비 완료')\n"
        "files.download('hanabot_finetuned.zip')")

# 파일 저장
output_path = Path(__file__).parent / "finetune_colab.ipynb"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=2)

print(f"✓ 노트북 생성 완료: {output_path}")
print(f"셀 개수: {len(notebook['cells'])}")
