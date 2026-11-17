# Google Colab에서 하나봇 파인튜닝하기

이 노트북은 Google Colab(T4 GPU)에서 하나봇 모델을 파인튜닝합니다.

## 📋 준비물

1. Google Colab 계정
2. `hanabot_train.jsonl` (학습 데이터, 270개)
3. `hanabot_eval.jsonl` (평가 데이터, 30개)

## 🚀 Colab 실행 순서

### 1️⃣ 노트북 열기
- Google Colab에서 이 노트북 열기
- 런타임: **T4 GPU** 선택 (무료 사용 가능)

### 2️⃣ 환경 설정 (셀 1-2)
```
셀 1: GPU 확인 및 라이브러리 설치
셀 2: Unsloth 설치 (3-5분 소요)
```

### 3️⃣ 모델 로드 (셀 3-4)
```
셀 3: Unsloth에서 Qwen2.5-3B-Instruct-bnb-4bit 모델 로드
셀 4: LoRA 어댑터 설정 (r=16, lora_alpha=16)
```

### 4️⃣ 데이터 준비 (셀 5-6)
```
셀 5: hanabot_train.jsonl 파일 업로드
셀 6: 데이터 로드 및 형식 확인
```

### 5️⃣ 학습 (셀 7-8)
```
셀 7: 트레이닝 파라미터 설정 (2 epoch, batch_size=4)
셀 8: 모델 학습 실행 (20-30분 소요)
```

### 6️⃣ 학습 모니터링 (셀 9)
```
셀 9: Loss 그래프 출력 (학습 과정 시각화)
```

### 7️⃣ 평가 (셀 10-11)
```
셀 10: hanabot_eval.jsonl에서 3개 질문 샘플링
셀 11: 학습 전후 모델 답변 비교 (형식, 거절 확인)
```

### 8️⃣ 모델 내보내기 (셀 12-13)
```
셀 12: 학습된 모델을 GGUF(q4_k_m) 형식으로 변환
셀 13: Modelfile 생성 (Ollama 호환)
```

### 9️⃣ 다운로드 (셀 14)
```
셀 14: GGUF 파일과 Modelfile을 zip으로 압축 후 다운로드
```

## 📥 결과 다운로드

Colab 실행 후:
1. `hanabot_finetuned.zip` 파일 다운로드
2. 로컬에서 압축 해제
3. `hanabot_finetuned.gguf` - 파인튜닝된 모델
4. `Modelfile` - Ollama 설정 파일

## 💻 로컬에서 사용 (Ollama)

```bash
# 로컬에서 모델 임포트
ollama create hanabot-finetuned -f ./Modelfile

# 모델 실행
ollama run hanabot-finetuned
```

## ⚠️ 주의사항

- **GPU 메모리**: T4(16GB)로 충분 (4비트 양자화 사용)
- **실행 시간**: 전체 약 1시간 (설치 10분 + 학습 30분)
- **파일 크기**: GGUF 약 2-3GB
- **Colab 세션**: 세션 종료 후 파일이 삭제되므로 반드시 다운로드할 것

## 🔧 커스터마이징

노트북 내에서 다음을 수정 가능:

```python
# 학습 파라미터
num_train_epochs = 2          # 에폭 수
per_device_train_batch_size = 4  # 배치 크기
max_steps = -1                # -1 = 전체 데이터

# LoRA 설정
r = 16                        # LoRA rank
lora_alpha = 16               # LoRA scaling
```

## 📞 문제 해결

| 문제 | 해결 |
|------|------|
| Out of Memory | 배치 크기 줄이기 (4→2) |
| 파일 업로드 실패 | 파일 크기 확인 (< 100MB) |
| 모델 로드 실패 | 인터넷 연결 확인, 셀 재실행 |

---

**작성자**: Claude  
**최종 수정**: 2026-11-17
