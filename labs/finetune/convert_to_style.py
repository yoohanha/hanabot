# [1-3] 데이터셋을 STYLE.md 형식으로 변환 (개선 버전)
import json
from pathlib import Path

# RAG_PLAN.md의 원문으로부터 STYLE.md 형식 답변 생성
STYLE_ANSWERS = {
    # 기초반
    "기초반": "[하나봇]\n- 4주 과정이며 월요일과 화요일에 수업합니다\n- 생성AI 기초, 프롬프트, 파이썬 기초, LangChain, RAG를 배웁니다\n자세한 내용은 학원 데스크로 문의해 주세요.",

    # 시간표
    "09:00": "[하나봇]\n- 102 실습실은 평일 09:00부터 21:00까지 쓸 수 있습니다\n- 수업이 없는 시간에는 실습실에서 자습할 수 있습니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "09:30": "[하나봇]\n- 오전 수업은 09:30부터 12:30까지 101 강의실에서 합니다\n- 오후 수업은 14:00부터 17:00까지 102 실습실에서 합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "월요일": "[하나봇]\n- 월요일은 기초반 수업입니다\n- 오전에는 생성AI 기초와 프롬프트, 오후에는 파이썬 기초를 배웁니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "화요일": "[하나봇]\n- 화요일은 기초반 수업입니다\n- 오전에는 LangChain, 오후에는 RAG를 배웁니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "수요일": "[하나봇]\n- 수요일은 실무반 수업입니다\n- 오전에는 Fine-tuning, 오후에는 LLMOps를 배웁니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "목요일": "[하나봇]\n- 목요일은 실무반 수업입니다\n- 오전에는 바이브코딩, 오후에는 웹 서비스(FastAPI)를 배웁니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "금요일": "[하나봇]\n- 금요일은 실무반 수업입니다\n- 오전에는 Docker와 Kubernetes를 배우고, 오후에는 프로젝트와 자습을 합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",

    # 수강 규칙
    "지각": "[하나봇]\n- 수업 시작 후 10분이 넘어서 들어오면 지각입니다\n- 지각 3회는 결석 1회로 처리합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "조퇴": "[하나봇]\n- 수업이 끝나기 30분 전보다 일찍 나가면 조퇴입니다\n- 조퇴 2회는 결석 1회로 처리합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "결석": "[하나봇]\n- 결석할 때는 전날 18시까지 데스크나 이메일로 알려야 합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "병결": "[하나봇]\n- 진단서를 내면 결석을 출석으로 인정합니다\n- 병결 인정은 한 과정에 2회까지입니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "수료": "[하나봇]\n- 출석률이 80% 이상이면 과정이 끝날 때 수료증을 받습니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "준비물": "[하나봇]\n- 수업에는 개인 노트북을 가져옵니다\n- 실습을 위해 RAM 16GB 이상인 노트북을 권장합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",

    # 수강료
    "30만": "[하나봇]\n- 기초반 수강료는 월 30만 원입니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "50만": "[하나봇]\n- 실무반 수강료는 월 50만 원입니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "할인": "[하나봇]\n- 같은 과정을 다시 들으면 수강료를 50% 할인합니다\n- 친구와 함께 등록하면 두 사람 모두 수강료를 10% 할인합니다\n- 할인은 중복되지 않으며, 둘 중 하나만 받을 수 있습니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "환불": "[하나봇]\n- 개강 전에 취소하면 수강료 전액을 환불합니다\n- 수업 기간의 1/3이 지나기 전에는 수강료의 2/3를 환불합니다\n- 수업 기간의 1/2이 지나기 전에는 수강료의 1/2을 환불합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",

    # 시설
    "GPU": "[하나봇]\n- 실습실의 GPU PC는 2시간 단위로 예약해서 씁니다\n- 한 사람이 하루 최대 4시간까지 쓸 수 있습니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "음식": "[하나봇]\n- 실습실에는 음식을 가져올 수 없습니다\n- 뚜껑이 있는 물은 가져와도 됩니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "분실물": "[하나봇]\n- 학원에서 찾은 분실물은 데스크에서 7일 동안 보관합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",

    # 보안
    "외부": "[하나봇]\n- 학원 자료와 수강생 정보를 ChatGPT 같은 외부 AI 서비스에 올리지 않습니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "Ollama": "[하나봇]\n- 하나 AI 학원의 실습은 각자 PC의 Ollama 모델(llama3.1)로 합니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "개인정보": "[하나봇]\n- 실습 데이터에는 실제 이름, 전화번호, 주민번호를 넣지 않습니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
    "보안규정": "[하나봇]\n- 보안 규정을 처음 어기면 경고를 받습니다\n- 두 번 어기면 해당 과정의 수강이 제한됩니다\n자세한 내용은 학원 데스크로 문의해 주세요.",
}

DEFAULT_REJECT = "[하나봇]\n- 규정 문서에서 찾을 수 없습니다\n자세한 내용은 학원 데스크로 문의해 주세요."


def convert_answer(original_answer):
    """원문 답변을 STYLE.md 형식으로 변환"""
    # 이미 STYLE.md 형식인지 확인
    if original_answer.startswith("[하나봇]"):
        return original_answer

    # 거절 형식인지 확인
    if "규정에 없는" in original_answer or original_answer.strip() == "# 학원 소개":
        return DEFAULT_REJECT

    # 원문 첫 줄을 보고 키워드 찾아서 매핑
    first_line = original_answer.split('\n')[0]

    # 각 키워드 확인 (더 정교한 매칭)
    for keyword, template in STYLE_ANSWERS.items():
        if keyword in original_answer or keyword in first_line:
            return template

    # 매칭 실패 → 기본 거절
    return DEFAULT_REJECT


def convert_dataset(input_file, output_file):
    """JSONL 파일 변환"""
    converted = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line.strip())
                conversations = item.get('conversations', [])

                # 답변 변환
                for conv in conversations:
                    if conv['role'] == 'assistant':
                        conv['content'] = convert_answer(conv['content'])

                converted.append(item)
            except Exception as e:
                print(f"⚠️  변환 오류: {e}")
                continue

    # 변환된 데이터 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in converted:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    return len(converted)


if __name__ == "__main__":
    new_dir = Path(__file__).parent.parent.parent / "data" / "finetune"
    new_dir.mkdir(parents=True, exist_ok=True)

    # labs/finetune의 원본 파일을 직접 읽어서 변환
    old_dir = Path(__file__).parent
    new_train = new_dir / "hanabot_train.jsonl"
    new_eval = new_dir / "hanabot_eval.jsonl"

    print("=" * 70)
    print("📝 데이터셋을 STYLE.md 형식으로 변환 중...\n")

    # 훈련 데이터 변환
    old_train_file = old_dir / "hanabot_train.jsonl"
    if old_train_file.exists():
        count = convert_dataset(old_train_file, new_train)
        print(f"✓ 훈련 데이터: {count}개 변환 완료")
        print(f"  저장: {new_train}\n")

    # 평가 데이터 변환
    old_eval_file = old_dir / "hanabot_eval.jsonl"
    if old_eval_file.exists():
        count = convert_dataset(old_eval_file, new_eval)
        print(f"✓ 평가 데이터: {count}개 변환 완료")
        print(f"  저장: {new_eval}\n")

    print("=" * 70)
    print("✅ 변환 완료!\n")
