# [1-3] finetune_colab.ipynb 수정
import json

with open('../1-3/finetune_colab.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Cell 12 수정
nb['cells'][12]['source'] = """import json
from datasets import Dataset

# 데이터 로드
data = []
with open(train_file, 'r', encoding='utf-8') as f:
    for line in f:
        data.append(json.loads(line))

print(f'총 {len(data)}개 데이터')

# Chat template으로 학습 텍스트 생성
texts = []
for item in data:
    text = tokenizer.apply_chat_template(
        item['conversations'],
        tokenize=False,
        add_generation_prompt=False
    )
    texts.append(text)

dataset = Dataset.from_dict({'text': texts})
print(f'샘플 텍스트: {texts[0][:100]}...')"""

# Cell 22 수정
nb['cells'][22]['source'] = """from unsloth import unsloth_to_gguf
import os

unsloth_to_gguf(
    model,
    tokenizer,
    quantization_method="q4_k_m",
    output_filename="hanabot_finetuned.gguf",
)

file_size = os.path.getsize("hanabot_finetuned.gguf") / 1e9
print(f'GGUF 변환 완료: {file_size:.1f}GB')"""

# Cell 24 수정 (Qwen TEMPLATE 추가)
qwen_template = r"""<|im_start|>user
{{ message['content'] }}<|im_end|>
"""

nb['cells'][24]['source'] = """modelfile = '''FROM ./hanabot_finetuned.gguf

TEMPLATE \"\"\"{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{% set ns = namespace(is_first=true) %}{% for message in messages %}{% if message['role'] == 'user' %}{% set ns.is_first = false %}<|im_start|>user
{{ message['content'] }}<|im_end|>
{% elif message['role'] == 'assistant' %}{% set ns.is_first = false %}<|im_start|>assistant
{{ message['content'] }}<|im_end|>
{% elif message['role'] == 'system' %}{% if not ns.is_first %}<|im_start|>user<|im_end|>
{% endif %}<|im_start|>system
{{ message['content'] }}<|im_end|>
{% set ns.is_first = false %}{% endif %}{% endfor %}{% if add_generation_prompt and ns.is_first %}{% elif add_generation_prompt %}<|im_start|>assistant
{% endif %}\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM "당신은 하나 AI 학원의 도우미 하나봇입니다. 학원 규정에 대한 질문에 답합니다."
'''

with open('Modelfile', 'w', encoding='utf-8') as f:
    f.write(modelfile)

print('Modelfile 생성 완료')"""

# Google Drive 저장 셀 추가
google_drive_md = {
    "cell_type": "markdown",
    "id": "cell-27",
    "metadata": {},
    "source": ["## 1️⃣4️⃣ Google Drive에 저장"]
}

google_drive_code = {
    "cell_type": "code",
    "execution_count": None,
    "id": "cell-28",
    "metadata": {},
    "outputs": [],
    "source": ["""from google.colab import drive
drive.mount('/content/drive')

drive_path = '/content/drive/My Drive/hanabot_finetune'
!mkdir -p "{drive_path}"
!cp hanabot_finetuned.gguf "{drive_path}/"
!cp Modelfile "{drive_path}/"
!cp hanabot_finetuned.zip "{drive_path}/"

print('Google Drive에 저장 완료')"""]
}

nb['cells'].append(google_drive_md)
nb['cells'].append(google_drive_code)

# 저장
with open('../1-3/finetune_colab.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("완료: 노트북 수정됨")
