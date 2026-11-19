#!/usr/bin/env python3
# [3-3] 웹 서비스 함수 (상담 신청, GPU 예약 등)

import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).parent.parent
CONSULTS_FILE = PROJECT_ROOT / 'web' / 'data' / 'consults.json'
RESERVES_FILE = PROJECT_ROOT / 'web' / 'data' / 'reserves.json'

# [3-4] GPU PC 예약 규칙 (맨 위에 모아놨음)
GPU_MIN_DURATION = 2  # 시간 단위
GPU_MAX_DURATION_PER_DAY = 4  # 하루 최대
GPU_WORK_START = 9  # 09:00
GPU_WORK_END = 21  # 21:00
GPU_PC_COUNT = 4  # GPU-1 ~ GPU-4

# [3-5] 수강 신청 규칙 (맨 위에 모아놨음)
BASIC_MONTHLY_FEE = 300000  # 기초반 월 30만 원
ADVANCED_MONTHLY_FEE = 500000  # 실무반 월 50만 원
RETAKE_DISCOUNT = 0.5  # 50% 할인
FRIEND_DISCOUNT = 0.1  # 10% 할인
ENROLLS_FILE = PROJECT_ROOT / 'web' / 'data' / 'enrolls.json'

# [3-3] 상담 신청 함수
def create_consult(student_id: str, course: str, desired_time: str, inquiry: str) -> dict:
    """
    상담 신청을 받고 저장.

    Args:
        student_id: 학번 (예: HANA-001)
        course: 관심 과정 (기초반, 실무반, 모름)
        desired_time: 희망 시간 (예: 10:30, 14:00)
        inquiry: 문의 내용

    Returns:
        dict: {'success': bool, 'message': str, 'consult_id': str (성공 시)}
    """

    # 1. 입력 검증
    empty_fields = []
    if not student_id or not student_id.strip():
        empty_fields.append('학번')
    if not course or course == '':
        empty_fields.append('관심 과정')
    if not desired_time or not desired_time.strip():
        empty_fields.append('희망 시간')
    if not inquiry or not inquiry.strip():
        empty_fields.append('문의 내용')

    if empty_fields:
        return {
            'success': False,
            'message': f"다음 항목을 입력해주세요: {', '.join(empty_fields)}"
        }

    # 2. 시간 검증 (평일 10:00~18:00만 가능)
    try:
        # 희망 시간 파싱 (HH:MM 형식)
        time_parts = desired_time.strip().split(':')
        if len(time_parts) != 2:
            raise ValueError()
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # 현재 요일 확인 (월=0, 일=6)
        now = datetime.now(ZoneInfo('Asia/Seoul'))
        weekday = now.weekday()

        # 주말 (토=5, 일=6) 확인
        if weekday >= 5:
            return {
                'success': False,
                'message': '상담은 평일 10:00~18:00에 가능해요'
            }

        # 평일이면 시간 확인 (10:00 ~ 18:00)
        total_minutes = hour * 60 + minute
        start_time = 10 * 60  # 10:00
        end_time = 18 * 60    # 18:00

        if total_minutes < start_time or total_minutes > end_time:
            return {
                'success': False,
                'message': '상담은 평일 10:00~18:00에 가능해요'
            }
    except (ValueError, IndexError):
        return {
            'success': False,
            'message': '시간을 HH:MM 형식으로 입력해주세요 (예: 14:30)'
        }

    # 3. 접수 번호 생성
    # 기존 파일에서 마지막 번호 읽기
    consult_number = 1
    if CONSULTS_FILE.exists():
        try:
            with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
                consults = json.load(f)
                if consults:
                    last_id = consults[-1]['consult_id']
                    # C-0001 형식에서 숫자만 추출
                    consult_number = int(last_id.split('-')[1]) + 1
        except (json.JSONDecodeError, IndexError):
            consult_number = 1

    consult_id = f"C-{consult_number:04d}"

    # 4. 데이터 저장
    consult_data = {
        'consult_id': consult_id,
        'student_id': student_id.strip(),
        'course': course,
        'desired_time': desired_time.strip(),
        'inquiry': inquiry.strip(),
        'created_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    }

    # 파일 로드 (없으면 빈 배열)
    consults = []
    if CONSULTS_FILE.exists():
        try:
            with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
                consults = json.load(f)
        except json.JSONDecodeError:
            consults = []

    # 데이터 추가
    consults.append(consult_data)

    # 파일 저장
    CONSULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(consults, f, ensure_ascii=False, indent=2)

    return {
        'success': True,
        'message': f'접수 완료했습니다. 접수 번호: {consult_id}',
        'consult_id': consult_id
    }


# [3-4] GPU PC 예약 함수
def reserve_gpu(student_id: str, date_str: str, start_time_str: str, duration: int, pc_number: int) -> dict:
    """
    GPU PC 예약을 받고 저장.

    Args:
        student_id: 학번 (예: HANA-001)
        date_str: 날짜 (YYYY-MM-DD)
        start_time_str: 시작 시각 (HH:MM)
        duration: 이용 시간 (2 또는 4)
        pc_number: PC 번호 (1~4)

    Returns:
        dict: {'success': bool, 'message': str, 'reserve_id': str (성공 시)}
    """

    # 1. 입력 검증
    empty_fields = []
    if not student_id or not student_id.strip():
        empty_fields.append('학번')
    if not date_str or not date_str.strip():
        empty_fields.append('날짜')
    if not start_time_str or not start_time_str.strip():
        empty_fields.append('시작 시각')
    if duration not in [2, 4]:
        return {
            'success': False,
            'message': '이용 시간은 2시간 또는 4시간만 가능해요'
        }
    if pc_number not in range(1, GPU_PC_COUNT + 1):
        return {
            'success': False,
            'message': f'PC 번호는 1~{GPU_PC_COUNT} 사이여야 해요'
        }

    if empty_fields:
        return {
            'success': False,
            'message': f"다음 항목을 입력해주세요: {', '.join(empty_fields)}"
        }

    # 2. 날짜 파싱 및 검증
    try:
        reserve_date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        # 지난 날짜 확인
        today = datetime.now(ZoneInfo('Asia/Seoul')).date()
        if reserve_date < today:
            return {
                'success': False,
                'message': '지나간 날짜로는 예약할 수 없어요'
            }
        # 평일만 (월=0, 일=6)
        if reserve_date.weekday() >= 5:
            return {
                'success': False,
                'message': '평일(월~금)에만 예약할 수 있어요'
            }
    except ValueError:
        return {
            'success': False,
            'message': '날짜를 YYYY-MM-DD 형식으로 입력해주세요 (예: 2026-11-20)'
        }

    # 3. 시간 파싱 및 검증
    try:
        time_parts = start_time_str.strip().split(':')
        if len(time_parts) != 2:
            raise ValueError()
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # 시간 범위 검증 (09:00 ~ 21:00)
        if hour < GPU_WORK_START or hour >= GPU_WORK_END or (hour == GPU_WORK_END and minute > 0):
            return {
                'success': False,
                'message': f'예약은 평일 {GPU_WORK_START:02d}:00 ~ {GPU_WORK_END:02d}:00 사이에만 가능해요'
            }

        # 종료 시간이 범위를 넘지 않는지 확인
        end_hour = hour + duration
        if end_hour > GPU_WORK_END:
            return {
                'success': False,
                'message': f'예약은 평일 {GPU_WORK_START:02d}:00 ~ {GPU_WORK_END:02d}:00 사이에만 가능해요'
            }
    except (ValueError, IndexError):
        return {
            'success': False,
            'message': '시각을 HH:MM 형식으로 입력해주세요 (예: 14:00)'
        }

    # 4. 기존 예약 로드
    reserves = []
    if RESERVES_FILE.exists():
        try:
            with open(RESERVES_FILE, 'r', encoding='utf-8') as f:
                reserves = json.load(f)
        except json.JSONDecodeError:
            reserves = []

    # 5. 같은 PC 중복 확인
    for reserve in reserves:
        if reserve['pc_number'] == pc_number and reserve['date'] == date_str:
            res_start = reserve['start_hour']
            res_duration = reserve['duration']
            res_end = res_start + res_duration

            # 시간 겹침 확인 (새 예약: hour ~ hour+duration)
            new_start = hour
            new_end = hour + duration
            if not (new_end <= res_start or new_start >= res_end):
                return {
                    'success': False,
                    'message': f'해당 시간에 GPU PC-{pc_number}은 이미 예약되어 있어요'
                }

    # 6. 같은 사람 하루 4시간 초과 확인
    same_day_total = 0
    for reserve in reserves:
        if reserve['student_id'] == student_id and reserve['date'] == date_str:
            same_day_total += reserve['duration']

    if same_day_total + duration > GPU_MAX_DURATION_PER_DAY:
        remaining = GPU_MAX_DURATION_PER_DAY - same_day_total
        return {
            'success': False,
            'message': f'하루 최대 {GPU_MAX_DURATION_PER_DAY}시간까지만 예약할 수 있어요 (남은 시간: {remaining}시간)'
        }

    # 7. 예약 번호 생성
    reserve_number = len([r for r in reserves if r['date'] == date_str]) + 1

    # 8. 데이터 저장
    reserve_data = {
        'reserve_id': f"R-{date_str.replace('-', '')}-{reserve_number:02d}",
        'student_id': student_id.strip(),
        'date': date_str,
        'start_hour': hour,
        'start_time': start_time_str.strip(),
        'duration': duration,
        'pc_number': pc_number,
        'created_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    }

    reserves.append(reserve_data)

    # 파일 저장
    RESERVES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESERVES_FILE, 'w', encoding='utf-8') as f:
        json.dump(reserves, f, ensure_ascii=False, indent=2)

    return {
        'success': True,
        'message': f'예약이 완료되었습니다. 예약 번호: {reserve_data["reserve_id"]}',
        'reserve_id': reserve_data['reserve_id']
    }


# [3-5] 수강료 계산 함수
def calc_fee(course: str, months: int, discount_type: str) -> dict:
    """
    수강료를 계산.

    Args:
        course: 과정 (기초반, 실무반)
        months: 개월 수
        discount_type: 할인 종류 (없음, 재수강, 친구)

    Returns:
        dict: {'original_fee': int, 'discount': int, 'final_fee': int, 'message': str}
    """

    # 1. 기본 금액 계산
    if course == '기초반':
        base_fee = BASIC_MONTHLY_FEE * months
    elif course == '실무반':
        base_fee = ADVANCED_MONTHLY_FEE * months
    else:
        return {'error': '과정을 정확히 선택해주세요'}

    # 2. 할인 적용
    discount_amount = 0
    discount_name = ''

    if discount_type == '재수강':
        discount_amount = int(base_fee * RETAKE_DISCOUNT)
        discount_name = '재수강 50% 할인'
    elif discount_type == '친구':
        discount_amount = int(base_fee * FRIEND_DISCOUNT)
        discount_name = '친구와 함께 10% 할인'

    final_fee = base_fee - discount_amount

    return {
        'original_fee': base_fee,
        'discount_amount': discount_amount,
        'discount_name': discount_name,
        'final_fee': final_fee,
        'message': f'원래 {base_fee:,}원 - {discount_name} {discount_amount:,}원 = 낼 금액 {final_fee:,}원' if discount_name else f'낼 금액: {final_fee:,}원'
    }


# [3-5] 수강 신청 함수
def enroll(student_id: str, course: str, months: int, discount_type: str) -> dict:
    """
    수강을 신청하고 저장.

    Args:
        student_id: 학번 (예: HANA-001)
        course: 과정 (기초반, 실무반)
        months: 개월 수
        discount_type: 할인 종류 (없음, 재수강, 친구)

    Returns:
        dict: {'success': bool, 'message': str, 'enroll_id': str, 'final_fee': int}
    """

    # 1. 입력 검증
    empty_fields = []
    if not student_id or not student_id.strip():
        empty_fields.append('학번')
    if not course or course == '':
        empty_fields.append('과정')
    if not months or months <= 0:
        empty_fields.append('개월 수')

    if empty_fields:
        return {
            'success': False,
            'message': f"다음 항목을 입력해주세요: {', '.join(empty_fields)}"
        }

    # 2. 금액 계산
    fee_result = calc_fee(course, months, discount_type)
    if 'error' in fee_result:
        return {'success': False, 'message': fee_result['error']}

    # 3. 신청 번호 생성
    enrolls = []
    if ENROLLS_FILE.exists():
        try:
            with open(ENROLLS_FILE, 'r', encoding='utf-8') as f:
                enrolls = json.load(f)
        except json.JSONDecodeError:
            enrolls = []

    enroll_number = len(enrolls) + 1
    enroll_id = f"E-{enroll_number:04d}"

    # 4. 데이터 저장
    enroll_data = {
        'enroll_id': enroll_id,
        'student_id': student_id.strip(),
        'course': course,
        'months': months,
        'discount_type': discount_type,
        'original_fee': fee_result['original_fee'],
        'discount_amount': fee_result['discount_amount'],
        'final_fee': fee_result['final_fee'],
        'created_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    }

    enrolls.append(enroll_data)

    # 파일 저장
    ENROLLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENROLLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(enrolls, f, ensure_ascii=False, indent=2)

    return {
        'success': True,
        'message': f'신청이 완료되었습니다. 신청 번호: {enroll_id}',
        'enroll_id': enroll_id,
        'final_fee': fee_result['final_fee']
    }
