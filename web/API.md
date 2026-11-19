# 하나 AI 학원 웹 API 정리

## 함수명과 API 짝

| 모듈 | 함수명 | HTTP 메서드 | 엔드포인트 | 목적 |
|-----|--------|-----------|-----------|------|
| services.py | `create_consult()` | POST | `/api/consult` | 상담 신청 |
| services.py | `reserve_gpu()` | POST | `/api/reserve` | GPU PC 예약 |
| services.py | `calc_fee()` | POST | `/api/fee` | 수강료 계산 |
| services.py | `enroll()` | POST | `/api/enroll` | 수강 신청 |
| services.py | - | GET | `/api/consult` | 모든 상담 조회 |
| services.py | - | GET | `/api/reserve` | 예약 현황 조회 |
| services.py | - | GET | `/api/enroll` | 모든 수강 조회 |
| services.py | - | GET | `/api/reserves` | 모든 예약 조회 |

---

## API 명세

### ① POST /api/consult - 상담 신청

**이름**: 상담 신청  
**주소**: `http://localhost:8080/api/consult`  
**HTTP**: POST

**보내는 값** (JSON)
```json
{
  "student_id": "HANA-001",
  "course": "기초반",
  "desired_time": "14:30",
  "inquiry": "일주일에 2번 수업이 가능합니다"
}
```

**돌려받는 값** (JSON)
```json
{
  "success": true,
  "message": "접수 완료했습니다. 접수 번호: C-0001",
  "consult_id": "C-0001"
}
```

**규칙**
- 평일 10:00~18:00만 접수 가능
- 빈 칸이 있으면 어느 칸인지 알려줌
- 외부 JSON 파일에 저장

---

### ② POST /api/reserve - GPU PC 예약

**이름**: GPU PC 예약  
**주소**: `http://localhost:8080/api/reserve`  
**HTTP**: POST

**보내는 값** (JSON)
```json
{
  "student_id": "HANA-001",
  "date": "2026-11-20",
  "start_time": "14:00",
  "duration": 2,
  "pc_number": 1
}
```

**돌려받는 값** (JSON)
```json
{
  "success": true,
  "message": "예약이 완료되었습니다. 예약 번호: R-20261120-01",
  "reserve_id": "R-20261120-01"
}
```

**규칙**
- 2시간 단위만 가능 (2 또는 4)
- 한 사람 하루 최대 4시간
- 평일 09:00~21:00 범위
- 같은 PC 같은 시간 중복 불가
- 지난 날짜 불가

---

### ③ POST /api/fee - 수강료 계산 (저장 안 함)

**이름**: 수강료 계산  
**주소**: `http://localhost:8080/api/fee`  
**HTTP**: POST

**보내는 값** (JSON)
```json
{
  "course": "실무반",
  "months": 2,
  "discount_type": "재수강"
}
```

**돌려받는 값** (JSON)
```json
{
  "original_fee": 1000000,
  "discount_amount": 500000,
  "discount_name": "재수강 50% 할인",
  "final_fee": 500000,
  "message": "원래 1,000,000원 - 재수강 50% 할인 500,000원 = 낼 금액 500,000원"
}
```

**규칙**
- 기초반: 월 30만 원
- 실무반: 월 50만 원
- 재수강: 50% 할인
- 친구와 함께: 10% 할인
- 중복 불가 (큰 할인만 적용)

---

### ④ POST /api/enroll - 수강 신청

**이름**: 수강 신청  
**주소**: `http://localhost:8080/api/enroll`  
**HTTP**: POST

**보내는 값** (JSON)
```json
{
  "student_id": "HANA-001",
  "course": "기초반",
  "months": 1,
  "discount_type": "없음"
}
```

**돌려받는 값** (JSON)
```json
{
  "success": true,
  "message": "신청이 완료되었습니다. 신청 번호: E-0001",
  "enroll_id": "E-0001",
  "final_fee": 300000
}
```

**규칙**
- 신청 번호 자동 생성 (E-0001, E-0002, ...)
- 모든 정보 JSON에 저장

---

### ⑤ GET /api/consult - 모든 상담 조회

**이름**: 상담 신청 목록  
**주소**: `http://localhost:8080/api/consult`  
**HTTP**: GET

**돌려받는 값** (JSON)
```json
{
  "consults": [
    {
      "consult_id": "C-0001",
      "student_id": "HANA-001",
      "course": "기초반",
      "desired_time": "14:30",
      "inquiry": "일주일에 2번 수업이 가능합니다",
      "created_at": "2026-11-19T10:30:00+09:00"
    }
  ]
}
```

---

### ⑥ GET /api/reserve?date=날짜 - 예약 현황 조회

**이름**: GPU PC 예약 현황  
**주소**: `http://localhost:8080/api/reserve?date=2026-11-20`  
**HTTP**: GET

**돌려받는 값** (JSON)
```json
{
  "date": "2026-11-20",
  "reserves": [
    {
      "reserve_id": "R-20261120-01",
      "student_id": "HANA-001",
      "date": "2026-11-20",
      "start_hour": 14,
      "start_time": "14:00",
      "duration": 2,
      "pc_number": 1,
      "created_at": "2026-11-19T10:00:00+09:00"
    }
  ]
}
```

---

### ⑦ GET /api/reserves - 모든 예약 조회

**이름**: 모든 GPU PC 예약  
**주소**: `http://localhost:8080/api/reserves`  
**HTTP**: GET

**돌려받는 값**: 위와 동일 (날짜 필터 없음)

---

### ⑧ GET /api/enroll - 모든 수강 조회

**이름**: 수강 신청 목록  
**주소**: `http://localhost:8080/api/enroll`  
**HTTP**: GET

**돌려받는 값** (JSON)
```json
{
  "enrolls": [
    {
      "enroll_id": "E-0001",
      "student_id": "HANA-001",
      "course": "기초반",
      "months": 1,
      "discount_type": "없음",
      "original_fee": 300000,
      "discount_amount": 0,
      "final_fee": 300000,
      "created_at": "2026-11-19T10:30:00+09:00"
    }
  ]
}
```

---

## 사용 예시

### 상담 신청 예시 (Python)
```python
import requests
import json

response = requests.post(
  'http://localhost:8080/api/consult',
  json={
    'student_id': 'HANA-001',
    'course': '기초반',
    'desired_time': '14:30',
    'inquiry': '일주일에 2번 수업이 가능합니다'
  }
)

result = response.json()
if result['success']:
    print(f"접수 완료: {result['consult_id']}")
else:
    print(f"오류: {result['message']}")
```

### GPU PC 예약 예시
```python
response = requests.post(
  'http://localhost:8080/api/reserve',
  json={
    'student_id': 'HANA-001',
    'date': '2026-11-20',
    'start_time': '14:00',
    'duration': 2,
    'pc_number': 1
  }
)
```

### 수강 신청 예시
```python
response = requests.post(
  'http://localhost:8080/api/enroll',
  json={
    'student_id': 'HANA-001',
    'course': '기초반',
    'months': 1,
    'discount_type': '없음'
  }
)
```
