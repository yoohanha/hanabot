# [1-3] finetune_colab.ipynb 최종 수정
import json

with open('../1-3/finetune_colab.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Cell 10 수정: 업로드 경로를 data/finetune/으로
nb['cells'][10]['source'] = """from google.colab import files

print('data/finetune/에서 hanabot_train.jsonl 파일을 선택해주세요')
uploaded = files.upload()
train_file = list(uploaded.keys())[0]
print(f'업로드됨: {train_file}')"""

# Cell 22 수정: unsloth_to_gguf → model.save_pretrained_gguf
nb['cells'][22]['source'] = """import os

# GGUF로 변환 (quantization 적용)
model.save_pretrained_gguf(
    "hanabot_finetuned.gguf",
    tokenizer=tokenizer,
    quantization_method="q4_k_m"
)

file_size = os.path.getsize("hanabot_finetuned.gguf") / 1e9
print(f'GGUF 변환 완료: {file_size:.1f}GB')"""

# 저장
with open('../1-3/finetune_colab.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("완료: unsloth_to_gguf → model.save_pretrained_gguf 변경됨")
