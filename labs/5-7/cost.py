#!/usr/bin/env python3
# [5-7] AWS GPU 서버 비용 계산기
# -*- coding: utf-8 -*-
import sys
import io

# [5-7] Windows UTF-8 출력 처리
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def calculate_costs():
    """
    # [5-7] 사용자 입력받기
    - 시간당 가격 (달러)
    - 환율 (원/달러)
    - 비용 계산 & 표 출력
    """

    # [5-7] 헤더 출력
    print("=" * 60)
    print("[5-7] AWS GPU 서버 (g4dn.xlarge) 비용 계산기")
    print("=" * 60)

    # [5-7] 사용자 입력 1: 시간당 가격 (달러)
    while True:
        try:
            hourly_rate = float(input("\n[시간당 가격 입력] (달러, 예: 0.52): $"))
            if hourly_rate < 0:
                print("[경고] 양수를 입력하세요.")
                continue
            break
        except ValueError:
            print("[경고] 숫자를 입력하세요.")

    # [5-7] 사용자 입력 2: 환율 (원/달러)
    while True:
        try:
            exchange_rate = float(input("[환율 입력] (원/달러, 예: 1300): KRW"))
            if exchange_rate < 0:
                print("[경고] 양수를 입력하세요.")
                continue
            break
        except ValueError:
            print("[경고] 숫자를 입력하세요.")

    # [5-7] 비용 계산
    # [5-7] 수업용 (2시간 사용)
    class_2h_usd = hourly_rate * 2
    class_2h_krw = class_2h_usd * exchange_rate

    # [5-7] 하루 켜둠 (24시간 × 1일)
    daily_usd = hourly_rate * 24
    daily_krw = daily_usd * exchange_rate

    # [5-7] 한 달 켜둠 (24시간 × 30일 = 720시간)
    monthly_usd = hourly_rate * 24 * 30
    monthly_krw = monthly_usd * exchange_rate

    # [5-7] 결과 표 출력
    print("\n" + "=" * 70)
    print("[비용 요약] (환율: KRW {:,.0f}/$)".format(exchange_rate))
    print("=" * 70)

    # [5-7] 헤더
    print(f"{'사용 패턴':<20} {'시간':<10} {'달러':<15} {'원화':<15}")
    print("-" * 70)

    # [5-7] 수업용 (2시간)
    print(f"{'[수업 2시간]':<20} {'2h':<10} "
          f"${class_2h_usd:>12.2f} {'KRW':>3}{class_2h_krw:>11,.0f}")

    # [5-7] 하루 켜둠
    print(f"{'[하루 켜둠]':<20} {'24h':<10} "
          f"${daily_usd:>12.2f} {'KRW':>3}{daily_krw:>11,.0f}")

    # [5-7] 한 달 켜둠
    print(f"{'[한 달 켜둠]':<20} {'720h':<10} "
          f"${monthly_usd:>12.2f} {'KRW':>3}{monthly_krw:>11,.0f}")

    print("=" * 70)

    # [5-7] 추가 정보
    print("\n[팁]")
    print(f"  - 시간당: ${hourly_rate:.2f} = KRW {hourly_rate * exchange_rate:,.0f}")
    print(f"  - 사용하지 않을 때는 EC2 중지 (비용 0원)")
    print(f"  - 중지 상태 EBS 스토리지: 약 KRW 500/월 (무시 가능)")
    print(f"  - 고정 IP 사용 시: 약 KRW 5,000/월 추가")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    # [5-7] 프로그램 실행
    try:
        calculate_costs()
    except KeyboardInterrupt:
        # [5-7] 사용자가 Ctrl+C 눌렀을 때
        print("\n\n[프로그램 종료]")
