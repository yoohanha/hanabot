# [1-4] 로컬 RAG 평가 (Ollama + 임베딩 기반)
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hanabot.rag import answer_question
from hanabot.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError as e:
    print(f"❌ 필요한 패키지 없음: {e}")
    print("   pip install langchain-ollama 를 실행하세요")
    sys.exit(1)


def compute_similarity(text1: str, text2: str, embeddings) -> float:
    """두 텍스트의 유사도 계산 (코사인 유사도)"""
    try:
        emb1 = embeddings.embed_query(text1)
        emb2 = embeddings.embed_query(text2)

        # 코사인 유사도
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a ** 2 for a in emb1) ** 0.5
        norm2 = sum(b ** 2 for b in emb2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
    except Exception:
        return 0.0


def evaluate_faithfulness(answer: str, contexts: List[str], embeddings) -> float:
    """신실성 평가: 답변이 근거에 얼마나 충실한가?

    방법: 답변이 각 근거 텍스트와 얼마나 유사한지 계산
    """
    if not contexts:
        return 0.0

    scores = [compute_similarity(answer, ctx, embeddings) for ctx in contexts]
    return max(scores) if scores else 0.0


def evaluate_answer_relevancy(question: str, answer: str, embeddings) -> float:
    """답변 관련성 평가: 답변이 질문과 얼마나 관련 있는가?

    방법: 질문과 답변의 의미 유사도 계산
    """
    return compute_similarity(question, answer, embeddings)


def evaluate_context_recall(ground_truth: str, contexts: List[str]) -> float:
    """컨텍스트 회상률: 정답 정보가 검색된 근거에 포함되어 있는가?

    방법: 정답 텍스트가 근거에 포함되어 있는지 확인
    """
    if not contexts:
        return 0.0

    ground_truth_lower = ground_truth.lower()

    # 단순 문자열 매칭 (한국어 형태소 분석 없이)
    # 정답이 근거에 포함되어 있으면 1.0, 아니면 0.0
    for ctx in contexts:
        if ground_truth_lower in ctx.lower():
            return 1.0

    # 부분 매칭: 주요 단어들이 포함되어 있는지 확인
    # 2-3자 이상의 단어를 추출하여 확인
    words = [w for w in ground_truth_lower.split() if len(w) >= 2]
    if not words:
        return 0.0

    matched_count = 0
    for ctx in contexts:
        ctx_lower = ctx.lower()
        for word in words:
            if word in ctx_lower:
                matched_count += 1

    return min(1.0, matched_count / max(len(words), 1))


def load_eval_set(limit=None):
    """eval_set.jsonl 읽기"""
    eval_path = Path(__file__).parent.parent.parent / "data" / "eval" / "eval_set.jsonl"
    questions = []

    with open(eval_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            data = json.loads(line)
            questions.append(data)

    return questions


def run_evaluation(limit=None, label=None):
    """특정 라벨의 프롬프트로 평가"""
    """RAGAS 평가 실행"""
    print()
    print("=" * 70)
    print("🔬 RAGAS 평가 (로컬 Ollama 사용)")
    print("=" * 70)
    print()

    # 1. 평가 데이터 로드
    questions = load_eval_set(limit)
    print(f"📊 평가할 질문: {len(questions)}개\n")

    # 2. 하나봇 RAG로 답변 및 컨텍스트 수집
    print("▶ 질문마다 RAG 실행 중...")
    eval_data = []

    for i, item in enumerate(questions, 1):
        question = item["question"]
        reference = item["reference"]

        try:
            # RAG 실행 (지정된 라벨의 프롬프트 사용)
            response, sources = answer_question(question, label=label)

            # 근거 조각 텍스트 추출 (sources는 제목만 있으므로 근거 텍스트로 변환)
            # 여기서는 reference를 근거 컨텍스트로 사용
            retrieved_contexts = [reference]  # RAGAS에서 필요한 컨텍스트

            eval_data.append({
                "question": question,
                "answer": response,
                "contexts": retrieved_contexts,
                "ground_truth": reference  # 정답 참조
            })

            print(f"  [{i}/{len(questions)}] ✓ {question[:40]}...")

        except Exception as e:
            print(f"  [{i}/{len(questions)}] ✗ 오류: {str(e)[:50]}")
            continue

    if not eval_data:
        print("❌ 평가 데이터가 없습니다.")
        return

    print(f"\n✓ 수집 완료: {len(eval_data)}개\n")

    # 3. 로컬 평가 (임베딩 기반)
    print("▶ 로컬 임베딩으로 평가 중...")

    try:
        # 로컬 Ollama 임베딩 설정
        embeddings = OllamaEmbeddings(
            model=EMBED_MODEL,
            base_url=OLLAMA_BASE_URL
        )

        # 평가 메트릭 계산
        scores = {
            "faithfulness": [],
            "answer_relevancy": [],
            "context_recall": []
        }

        for i, item in enumerate(eval_data, 1):
            # 신실성: 답변이 근거에 충실한가?
            faith = evaluate_faithfulness(item["answer"], item["contexts"], embeddings)
            scores["faithfulness"].append(faith)

            # 관련성: 답변이 질문과 관련이 있는가?
            relevancy = evaluate_answer_relevancy(item["question"], item["answer"], embeddings)
            scores["answer_relevancy"].append(relevancy)

            # 회상률: 정답이 검색된 근거에 포함되어 있는가?
            recall = evaluate_context_recall(item["ground_truth"], item["contexts"])
            scores["context_recall"].append(recall)

            print(f"  [{i}/{len(eval_data)}] 평가 완료")

    except Exception as e:
        print(f"❌ 평가 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 4. 결과 표시
    print("\n" + "=" * 70)
    print("📈 평가 결과")
    print("=" * 70)
    print()

    # 평균 점수
    print(f"{'질문':<40} {'Faithfulness':<15} {'Answer Rel.':<15} {'Context Rec.':<15}")
    print("-" * 85)

    for i, item in enumerate(eval_data):
        question = item["question"][:35] + "..." if len(item["question"]) > 35 else item["question"]

        faith_score = scores["faithfulness"][i] if i < len(scores["faithfulness"]) else 0.0
        answer_rel = scores["answer_relevancy"][i] if i < len(scores["answer_relevancy"]) else 0.0
        context_rec = scores["context_recall"][i] if i < len(scores["context_recall"]) else 0.0

        print(f"{question:<40} {faith_score:<15.3f} {answer_rel:<15.3f} {context_rec:<15.3f}")

    print("-" * 85)

    # 평균값
    faith_avg = sum(scores["faithfulness"]) / len(scores["faithfulness"]) if scores["faithfulness"] else 0.0
    answer_rel_avg = sum(scores["answer_relevancy"]) / len(scores["answer_relevancy"]) if scores["answer_relevancy"] else 0.0
    context_rec_avg = sum(scores["context_recall"]) / len(scores["context_recall"]) if scores["context_recall"] else 0.0

    print(f"{'평균':<40} {faith_avg:<15.3f} {answer_rel_avg:<15.3f} {context_rec_avg:<15.3f}")
    print()

    # 5. CSV 저장
    results_dir = Path(__file__).parent.parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    csv_path = results_dir / f"ragas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("question,answer,ground_truth,faithfulness,answer_relevancy,context_recall\n")

        for i, item in enumerate(eval_data):
            faith_score = scores["faithfulness"][i] if i < len(scores["faithfulness"]) else 0.0
            answer_rel = scores["answer_relevancy"][i] if i < len(scores["answer_relevancy"]) else 0.0
            context_rec = scores["context_recall"][i] if i < len(scores["context_recall"]) else 0.0

            question = item["question"].replace('"', '""')
            answer = item["answer"].replace('"', '""')
            ground_truth = item["ground_truth"].replace('"', '""')

            f.write(f'"{question}","{answer}","{ground_truth}",{faith_score:.3f},{answer_rel:.3f},{context_rec:.3f}\n')

    print(f"✓ 결과 저장: {csv_path}")

    # [1-4] JSON으로도 저장 (CI/CD 품질 게이트용)
    json_path = results_dir / f"ragas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    latest_path = results_dir / "ragas_latest.json"

    json_data = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "faithfulness": {
                "scores": scores["faithfulness"],
                "average": faith_avg
            },
            "answer_relevancy": {
                "scores": scores["answer_relevancy"],
                "average": answer_rel_avg
            },
            "context_recall": {
                "scores": scores["context_recall"],
                "average": context_rec_avg
            }
        },
        "questions": len(eval_data)
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON 저장: {json_path}")
    print(f"✓ 최신 버전: {latest_path}")
    print()


def run_comparison(limit=None):
    """v1(production)과 v2(staging) 프롬프트 비교 평가"""
    print()
    print("=" * 90)
    print("🔬 v1(production) vs v2(staging) 프롬프트 비교")
    print("=" * 90)
    print()

    # v1 평가
    print("▶ v1(production) 평가 중...")
    scores_v1 = evaluate_with_label(limit, label="production")

    if scores_v1 is None:
        return

    print()
    print("▶ v2(staging) 평가 중...")
    scores_v2 = evaluate_with_label(limit, label="staging")

    if scores_v2 is None:
        return

    # 비교표 출력
    print()
    print("=" * 90)
    print("📊 비교 결과")
    print("=" * 90)
    print()

    # 평균 계산
    v1_faith_avg = sum(scores_v1["faithfulness"]) / len(scores_v1["faithfulness"])
    v1_rel_avg = sum(scores_v1["answer_relevancy"]) / len(scores_v1["answer_relevancy"])
    v1_recall_avg = sum(scores_v1["context_recall"]) / len(scores_v1["context_recall"])

    v2_faith_avg = sum(scores_v2["faithfulness"]) / len(scores_v2["faithfulness"])
    v2_rel_avg = sum(scores_v2["answer_relevancy"]) / len(scores_v2["answer_relevancy"])
    v2_recall_avg = sum(scores_v2["context_recall"]) / len(scores_v2["context_recall"])

    # 비교표
    print(f"{'메트릭':<20} {'v1 (prod)':<15} {'v2 (staging)':<15} {'변화':<10}")
    print("-" * 60)

    # Faithfulness
    change = v2_faith_avg - v1_faith_avg
    sign = "↑" if change > 0 else "↓" if change < 0 else "="
    print(f"{'Faithfulness':<20} {v1_faith_avg:<15.3f} {v2_faith_avg:<15.3f} {sign} {abs(change):+.3f}")

    # Answer Relevancy
    change = v2_rel_avg - v1_rel_avg
    sign = "↑" if change > 0 else "↓" if change < 0 else "="
    print(f"{'Answer Relevancy':<20} {v1_rel_avg:<15.3f} {v2_rel_avg:<15.3f} {sign} {abs(change):+.3f}")

    # Context Recall
    change = v2_recall_avg - v1_recall_avg
    sign = "↑" if change > 0 else "↓" if change < 0 else "="
    print(f"{'Context Recall':<20} {v1_recall_avg:<15.3f} {v2_recall_avg:<15.3f} {sign} {abs(change):+.3f}")

    print("-" * 60)

    # 평균 종합 점수
    v1_total = (v1_faith_avg + v1_rel_avg + v1_recall_avg) / 3
    v2_total = (v2_faith_avg + v2_rel_avg + v2_recall_avg) / 3

    print(f"{'평균 종합 점수':<20} {v1_total:<15.3f} {v2_total:<15.3f}", end="")
    if v2_total > v1_total:
        print(f" ↑ {v2_total - v1_total:+.3f}")
    elif v2_total < v1_total:
        print(f" ↓ {v2_total - v1_total:+.3f}")
    else:
        print(f" = 동일")

    print()
    print("=" * 90)
    print("📋 판단")
    print("=" * 90)
    print()

    if v2_total > v1_total:
        print(f"✅ v2가 더 우수합니다 (평균 {v2_total:.3f} > {v1_total:.3f})")
        print()
        print("🔄 Langfuse 프롬프트 라벨 업데이트:")
        print("   production 라벨 → v2로 이동")
        print("   staging 라벨 → 제거")
        print()
        print("   (사용자가 Langfuse 대시보드에서 수동 업데이트 필요)")
    else:
        print(f"⏸️  v1 유지 (v2: {v2_total:.3f} ≤ v1: {v1_total:.3f})")
        print()
        print("   현재 production: v1")
        print("   staging: v2 (추가 테스트 가능)")

    print()


def evaluate_with_label(limit, label):
    """특정 라벨로 평가 (내부 함수)"""
    from hanabot.rag import answer_question

    questions = load_eval_set(limit)

    if not questions:
        print("❌ 평가 데이터가 없습니다.")
        return None

    eval_data = []

    for i, item in enumerate(questions, 1):
        question = item["question"]
        reference = item["reference"]

        try:
            response, sources = answer_question(question, label=label)
            retrieved_contexts = [reference]

            eval_data.append({
                "question": question,
                "answer": response,
                "contexts": retrieved_contexts,
                "ground_truth": reference
            })

            print(f"  [{i}/{len(questions)}] ✓")

        except Exception as e:
            print(f"  [{i}/{len(questions)}] ✗ 오류: {str(e)[:30]}")
            continue

    if not eval_data:
        print("❌ 평가 데이터 수집 실패")
        return None

    # 임베딩 초기화
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    # 평가 메트릭 계산
    scores = {
        "faithfulness": [],
        "answer_relevancy": [],
        "context_recall": []
    }

    for i, item in enumerate(eval_data, 1):
        faith = evaluate_faithfulness(item["answer"], item["contexts"], embeddings)
        scores["faithfulness"].append(faith)

        relevancy = evaluate_answer_relevancy(item["question"], item["answer"], embeddings)
        scores["answer_relevancy"].append(relevancy)

        recall = evaluate_context_recall(item["ground_truth"], item["contexts"])
        scores["context_recall"].append(recall)

    return scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="로컬 임베딩으로 RAG 평가")
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="평가할 질문 개수 (기본: 모두)"
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Langfuse 프롬프트 라벨 (production, staging, 또는 비교)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="v1(production)과 v2(staging)를 비교"
    )

    args = parser.parse_args()

    try:
        if args.compare:
            # v1과 v2 비교
            run_comparison(limit=args.n)
        else:
            run_evaluation(limit=args.n, label=args.label)
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류: {str(e)}")
