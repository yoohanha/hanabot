#!/usr/bin/env python3
# [3-6] 웹 API 자동 테스트 스크립트

import requests
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BASE_URL = "http://localhost:8080"

# 테스트 색상
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text):
    print(f"\n{BOLD}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{RESET}\n")

def print_result(test_name, success, expected):
    status = f"{GREEN}✅ PASS{RESET}" if success == expected else f"{RED}❌ FAIL{RESET}"
    print(f"  {test_name:40} {status}")

def test_consult_api():
    print_header("① 상담 신청 API 테스트")

    # 테스트 1: 정상 신청
    print(f"{BOLD}테스트 1: 정상 신청 (평일 14:30){RESET}")
    response = requests.post(f"{BASE_URL}/api/consult", json={
        "student_id": "HANA-TEST-001",
        "course": "기초반",
        "desired_time": "14:30",
        "inquiry": "테스트 신청입니다"
    })
    result = response.json()
    success = result.get('success', False)
    print_result("정상 신청", success, True)
    if success:
        print(f"    └─ 접수번호: {result['consult_id']}\n")

    # 테스트 2: 시간 외 신청
    print(f"{BOLD}테스트 2: 시간 외 신청 (08:00){RESET}")
    response = requests.post(f"{BASE_URL}/api/consult", json={
        "student_id": "HANA-TEST-002",
        "course": "실무반",
        "desired_time": "08:00",
        "inquiry": "아침 상담이 가능한가요?"
    })
    result = response.json()
    success = result.get('success', False)
    print_result("시간 외 거부", success, False)
    if not success:
        print(f"    └─ 메시지: {result['message']}\n")

    # 테스트 3: 빈 칸 신청
    print(f"{BOLD}테스트 3: 빈 칸 신청 (학번 없음){RESET}")
    response = requests.post(f"{BASE_URL}/api/consult", json={
        "student_id": "",
        "course": "기초반",
        "desired_time": "14:30",
        "inquiry": "테스트"
    })
    result = response.json()
    success = result.get('success', False)
    print_result("빈 칸 거부", success, False)
    if not success:
        print(f"    └─ 메시지: {result['message']}\n")

def test_reserve_api():
    print_header("② GPU PC 예약 API 테스트")

    # 테스트 날짜 설정 (내일 평일)
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    tomorrow = today + timedelta(days=1)
    while tomorrow.weekday() >= 5:
        tomorrow += timedelta(days=1)
    test_date = tomorrow.strftime('%Y-%m-%d')

    # 테스트 1: 정상 예약
    print(f"{BOLD}테스트 1: 정상 예약 (2시간){RESET}")
    response = requests.post(f"{BASE_URL}/api/reserve", json={
        "student_id": "HANA-TEST-001",
        "date": test_date,
        "start_time": "14:00",
        "duration": 2,
        "pc_number": 1
    })
    result = response.json()
    success = result.get('success', False)
    print_result("2시간 예약", success, True)
    if success:
        print(f"    └─ 예약번호: {result['reserve_id']}\n")

    # 테스트 2: 3시간 예약 (불가능)
    print(f"{BOLD}테스트 2: 3시간 예약 (불가능){RESET}")
    response = requests.post(f"{BASE_URL}/api/reserve", json={
        "student_id": "HANA-TEST-002",
        "date": test_date,
        "start_time": "10:00",
        "duration": 3,
        "pc_number": 2
    })
    result = response.json()
    success = result.get('success', False)
    print_result("3시간 거부", success, False)
    if not success:
        print(f"    └─ 메시지: {result['message']}\n")

    # 테스트 3: 범위 초과 (20:00 + 2시간)
    print(f"{BOLD}테스트 3: 범위 초과 (20:00 시작){RESET}")
    response = requests.post(f"{BASE_URL}/api/reserve", json={
        "student_id": "HANA-TEST-003",
        "date": test_date,
        "start_time": "20:00",
        "duration": 2,
        "pc_number": 3
    })
    result = response.json()
    success = result.get('success', False)
    print_result("범위 초과 거부", success, False)
    if not success:
        print(f"    └─ 메시지: {result['message']}\n")

def test_enroll_api():
    print_header("③ 수강 신청 API 테스트")

    # 테스트 1: 정상 신청
    print(f"{BOLD}테스트 1: 정상 신청 (기초반 1개월 할인 없음){RESET}")
    response = requests.post(f"{BASE_URL}/api/enroll", json={
        "student_id": "HANA-TEST-001",
        "course": "기초반",
        "months": 1,
        "discount_type": "없음"
    })
    result = response.json()
    success = result.get('success', False)
    print_result("정상 신청", success, True)
    if success:
        print(f"    └─ 신청번호: {result['enroll_id']}, 금액: {result['final_fee']:,}원\n")

    # 테스트 2: 재수강 할인
    print(f"{BOLD}테스트 2: 재수강 할인 (실무반 2개월 50%){RESET}")
    response = requests.post(f"{BASE_URL}/api/enroll", json={
        "student_id": "HANA-TEST-002",
        "course": "실무반",
        "months": 2,
        "discount_type": "재수강"
    })
    result = response.json()
    success = result.get('success', False)
    print_result("재수강 신청", success, True)
    if success:
        print(f"    └─ 신청번호: {result['enroll_id']}, 금액: {result['final_fee']:,}원\n")

    # 테스트 3: 친구 할인
    print(f"{BOLD}테스트 3: 친구 할인 (실무반 1개월 10%){RESET}")
    response = requests.post(f"{BASE_URL}/api/enroll", json={
        "student_id": "HANA-TEST-003",
        "course": "실무반",
        "months": 1,
        "discount_type": "친구"
    })
    result = response.json()
    success = result.get('success', False)
    print_result("친구 신청", success, True)
    if success:
        print(f"    └─ 신청번호: {result['enroll_id']}, 금액: {result['final_fee']:,}원\n")

def test_query_apis():
    print_header("④ 조회 API 테스트")

    # 모든 상담 조회
    print(f"{BOLD}상담 신청 목록 조회{RESET}")
    response = requests.get(f"{BASE_URL}/api/consult")
    result = response.json()
    consults = result.get('consults', [])
    success = len(consults) > 0
    print_result("상담 조회", success, True)
    print(f"    └─ 총 {len(consults)}건\n")

    # 모든 예약 조회
    print(f"{BOLD}GPU PC 예약 목록 조회{RESET}")
    response = requests.get(f"{BASE_URL}/api/reserves")
    result = response.json()
    reserves = result.get('reserves', [])
    success = len(reserves) > 0
    print_result("예약 조회", success, True)
    print(f"    └─ 총 {len(reserves)}건\n")

    # 모든 수강 조회
    print(f"{BOLD}수강 신청 목록 조회{RESET}")
    response = requests.get(f"{BASE_URL}/api/enroll")
    result = response.json()
    enrolls = result.get('enrolls', [])
    success = len(enrolls) > 0
    print_result("수강 조회", success, True)
    print(f"    └─ 총 {len(enrolls)}건\n")

def main():
    print(f"\n{BOLD}🤖 하나봇 웹 API 자동 테스트{RESET}")
    print(f"서버: {BASE_URL}\n")

    try:
        # 서버 연결 확인
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print(f"{GREEN}✅ 서버 연결 성공{RESET}\n")
    except Exception as e:
        print(f"{RED}❌ 서버 연결 실패: {e}{RESET}")
        print(f"서버를 먼저 시작해주세요: python web/server.py\n")
        return

    try:
        test_consult_api()
        test_reserve_api()
        test_enroll_api()
        test_query_apis()

        print_header("📋 테스트 완료")
        print(f"{GREEN}모든 API 테스트가 완료되었습니다!{RESET}\n")
        print("📌 주의: 테스트용 데이터를 삭제하려면 다음 파일들을 지워주세요:")
        print("   - web/data/consults.json")
        print("   - web/data/reserves.json")
        print("   - web/data/enrolls.json\n")

    except Exception as e:
        print(f"{RED}❌ 테스트 오류: {e}{RESET}\n")

if __name__ == '__main__':
    main()
