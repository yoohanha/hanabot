# [5-7] AWS GPU 서버 배포 가이드

## 🎯 목표
하나봇을 AWS EC2 GPU 인스턴스에서 실행하기
- Ollama (llama3.1 · bge-m3)
- 하나봇 에이전트 팀 (5부 완성 모델)
- 웹 인터페이스 (FastAPI)

---

## 📋 필요한 것

### AWS 계정 & 권한
- EC2, IAM, 보안 그룹 생성 권한
- 비용: `g4dn.xlarge` (약 $0.52/시간)

### 로컬 준비
- PuTTY 또는 SSH 클라이언트
- `.pem` 파일 (EC2 Key Pair - **절대 커밋 금지**)

---

## 🚀 배포 순서 (AWS 콘솔)

### 1️⃣ EC2 인스턴스 생성

#### 1. AMI 선택
1. AWS 콘솔 → **EC2** → **인스턴스 시작**
2. **AMI 선택**
   - 검색어: `Deep Learning Base`
   - AWS 제공: **Deep Learning Base (Ubuntu)**
   - GPU 드라이버 · CUDA · cuDNN 미리 설치됨
   - 비용 최소화: 무료 계층 아님 (GPU 필요)

#### 2. 인스턴스 타입 선택
- **GPU 필수**: `g4dn.xlarge` (Nvidia T4 × 1)
  - 가격: ~$0.52/시간
  - 메모리: 16 GB
  - vCPU: 4
- 개발용: `t3.medium` (CPU만, 테스트용 비추천)

#### 3. 네트워크 설정
1. **VPC**: 기본값 (default-vpc)
2. **서브넷**: 기본값
3. **자동 공인 IP 할당**: **활성화**
4. **IAM 인스턴스 프로필**: 없음 (기본값)

#### 4. 스토리지 설정
- **크기**: 100 GB (모델 저장 공간)
- **유형**: gp3 (일반 목적)
- **암호화**: 기본값

#### 5. 보안 그룹 설정 (중요!)
1. **새로운 보안 그룹 생성**: `hanabot-sg`
2. **인바운드 규칙** 추가:
   | 유형 | 프로토콜 | 포트 | 소스 | 용도 |
   |------|---------|------|------|------|
   | SSH | TCP | 22 | 0.0.0.0/0 | 원격 접속 |
   | HTTP | TCP | 80 | 0.0.0.0/0 | 웹 서버 |
   | HTTP | TCP | 8080 | 0.0.0.0/0 | 하나봇 웹 (FastAPI) |
   | ~~HTTP~~ | ~~TCP~~ | ~~11434~~ | ~~0.0.0.0/0~~ | ~~Ollama (내부용, 차단)~~ |

3. **아웃바운드 규칙**: 기본값 (모든 트래픽 허용)

#### 6. 키 페어 설정
1. **새 키 페어 생성**: `hanabot-key`
2. **형식**: `.pem` (Linux/Mac) 또는 `.ppk` (PuTTY)
3. **저장**: `.pem` 파일을 **안전한 곳**에 보관
   - **⚠️ 절대 GitHub에 커밋하지 말 것**
   - `.gitignore`에 `*.pem` 추가됨

#### 7. 인스턴스 시작
- **태그**: `Name: hanabot-gpu-server`
- **시작** 클릭

---

### 2️⃣ 초기화 스크립트 실행

#### 대기
- 인스턴스 상태: **running** (약 2-3분)
- 상태 확인: **2/2 passed** (약 5분)

#### 초기화 자동 실행
1. **user_data.sh** 가 자동으로 실행됨 (백그라운드)
2. **모니터링**:
   ```bash
   # EC2 인스턴스 선택 → 모니터링 탭 → 시스템 로그 확인
   ```
3. **예상 소요 시간**: 20-30분
   - Ollama 설치: 2분
   - 모델 다운로드: 15-20분 (llama3.1 · bge-m3)
   - 하나봇 클론 & 빌드: 3-5분

---

### 3️⃣ SSH 접속 & 상태 확인

#### SSH 접속
```bash
# [5-7] PEM 파일 권한 설정 (처음만)
chmod 400 hanabot-key.pem

# [5-7] EC2 접속 (공인 IP 주소 사용)
ssh -i hanabot-key.pem ubuntu@<EC2_공인_IP>
```

#### 초기화 상태 확인
```bash
# [5-7] 초기화 로그 확인 (실시간)
tail -f /var/log/hanabot-setup.log

# [5-7] user_data 스크립트 종료 여부 (완료 시 "완료" 메시지)
cloud-init status
```

#### 서비스 상태 확인
```bash
# [5-7] Ollama 상태
systemctl status ollama

# [5-7] Docker 상태
systemctl status docker

# [5-7] 하나봇 컨테이너 실행 여부
docker ps | grep hanabot
```

---

### 4️⃣ 접속 & 테스트

#### 하나봇 웹 열기
```
http://<EC2_공인_IP>:8080
```

#### Ollama 상태 확인
```bash
# [5-7] EC2 내부에서
curl http://localhost:11434/api/tags

# [5-7] 로컬에서 (보안 그룹에서 11434 차단됨)
# 접근 불가 ✗ (의도적 · Ollama는 웹 서버 경유로만 사용)
```

#### 로그 확인
```bash
# [5-7] 하나봇 컨테이너 로그
docker logs -f hanabot-app

# [5-7] 초기화 로그
cat /var/log/hanabot-setup.log
```

---

## 💾 백업 & 복구

### 체크포인트 저장
```bash
# [5-7] 체크포인트 다운로드 (로컬로)
scp -i hanabot-key.pem ubuntu@<IP>:/home/ubuntu/hanabot/labs/5-5/data/* ./local-backup/
```

### AMI 생성 (스냅샷)
1. **EC2 인스턴스 선택** → **이미지 및 템플릿** → **AMI 생성**
2. **이름**: `hanabot-gpu-ready`
3. **설명**: 모델 다운로드 완료 · 준비 완료
4. 이후 이 AMI로 빠르게 새 인스턴스 생성 가능

---

## 🛑 종료 & 비용 절감

### 임시 종료 (데이터 유지)
```bash
# AWS 콘솔: 인스턴스 선택 → 인스턴스 상태 → 중지
# 비용: 0 (EBS 스토리지만 과금)
# 재시작: 1-2분
```

### 완전 삭제
```bash
# AWS 콘솔: 인스턴스 선택 → 인스턴스 상태 → 종료
# 주의: 데이터 삭제됨 (백업 필수!)
```

---

## ⚠️ 주의사항

### 보안
- **`.pem` 파일**: 절대 공개하지 말 것 (암호와 동일)
- **보안 그룹**: 개발 종료 후 22 (SSH) · 8080 (웹) 닫기
- **방화벽**: 프로덕션은 IP 화이트리스트 추천

### 비용
- **g4dn.xlarge**: $0.52/시간 × 24시간 × 30일 = **약 $374/월**
- **비용 절감**: 사용 안 할 때는 **중지** (데이터 유지) 또는 **삭제**
- **예산 알림**: AWS Billing → 예산 설정

### 모델 다운로드
- **첫 시작**: 20-30분 소요 (인터넷 속도에 따라 다름)
- **재시작**: 모델 캐시 (스토리지에 저장되므로 빠름)
- **다시 다운받지 않음**: EBS 스토리지에 저장됨

---

## 🔧 문제 해결

### Ollama 모델 다운로드 실패
```bash
# [5-7] EC2에서 모니터링 로그 확인
tail -100 /var/log/hanabot-setup.log

# [5-7] Ollama 수동 모델 풀 (필요 시)
ollama pull llama3.1
ollama pull bge-m3
```

### 웹 서버 접속 불가
```bash
# [5-7] 컨테이너 상태 확인
docker ps -a

# [5-7] 로그 확인
docker logs hanabot-app

# [5-7] 포트 확인 (8080 사용 여부)
netstat -tuln | grep 8080
```

### SSH 접속 불가
1. **보안 그룹**: 22 포트 열렸는지 확인
2. **공인 IP**: 맞는 IP 사용했는지 확인
3. **`.pem` 권한**: `chmod 400 hanabot-key.pem`

---

## 📚 참고 자료

- [AWS EC2 문서](https://docs.aws.amazon.com/ec2/)
- [Deep Learning Base 소개](https://docs.aws.amazon.com/dlami/latest/userguide/overview.html)
- [Ollama 공식 가이드](https://github.com/ollama/ollama)
- [Docker 공식 문서](https://docs.docker.com/)

---

**🎉 성공! 하나봇 GPU 서버가 AWS에서 실행 중입니다.**
