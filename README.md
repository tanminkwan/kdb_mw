# 🛠️ MWM (Middleware Management System) - 리발소

<p align="center">
  <img src="app/static/img/mwm_banner.png" alt="MWM Banner" width="800">
</p>

## 📋 프로젝트 개요
**리발소(리포트 발송 소형 엔진)**는 미들웨어(WAS, WEB) 및 IT 자산의 상태를 모니터링하고, 변경 사항을 대사(Compare)하며, Kroki 기반의 Mermaid 다이어그램을 포함한 고급 이메일 리포트를 생성하는 통합 관리 솔루션입니다.

## ✨ 주요 기능 및 특징

### 🔍 미들웨어 관리 & 자동화
- **실시간 모니터링**: JEUS, WebToB 인스턴스 상태 추적 및 장애 탐지.
- **유연한 데이터 수집(Agent DML)**: 
  - 정규표현식(Regex) 기반 파일 매칭 지원 (`domain.*\.xml` 등).
  - 설치 경로 분석을 통한 도메인 ID 자동 추출 및 PK 매칭.
  - 설정 파일 변경분 대사(DeepDiff) 및 히스토리 관리.
- **가시성 최적화**: WAS/WEB 간의 복잡한 연결 관계를 시각화한 Relationship Diagram 제공.

### 🛡️ 데이터 정합성 & 보안
- **Host ID 표준화**: 시스템 전반의 `host_id`를 소문자로 강제 통일하여 대소문자 불이치로 인한 장애 원천 차단 (SQLAlchemy Validator 적용).
- **지식정보 그룹 권한**: Role 기반 접근제어(UtKmGroup)를 통한 콘텐츠 보안 강화.
- **중복 작업 방지**: 스케줄러 내 중복 Job 등록 방지 및 실행 시간 보정 로직(5s Buffer) 내장.

### 📧 고급 리포팅 & 협업
- **Smart Emailing**:
  - Mermaid 다이어그램을 이미지로 자동 변환하여 본문 삽입 (CID Embedding).
  - Select2 기반의 유연한 수신자 선택 (태그 그룹 + 직접 입력).
- **콘텐츠 관리**: Markdown/HTML 기반 지식베이스 구축 및 이메일 연동.

## 🏗️ 시스템 아키텍처

- **Backend**: Python 3.12, Flask 2.2+, Flask-AppBuilder
- **Persistent Scheduler**: 
  - **SQLAlchemyJobStore** 도입으로 스케줄 정보 DB 영구 저장.
  - Multi-Worker(Gunicorn) 환경에서도 안전한 단일 스케줄러 인스턴스 보장.
- **Storage/Cache**: PostgreSQL 16+, Redis 7+ (Session & Cache)
- **Engine 연동**: Kroki (Mermaid 렌더링), MinIO/S3 (오브젝트 스토리지)

## 📂 디렉토리 구조
- `app/api`: 데이터 수집 및 외부 연동 API
- `app/models`: IT 자산 및 미들웨어 통합 데이터 모델 (host_id 자동 정규화 내장)
- `app/sqls`: 비즈니스 로직 최적화 및 복합 쿼리 관리
- `app/dmls*`: 에이전트 수집 데이터의 정규화 및 트랜잭션 처리
- `docs/`: 마이그레이션 가이드 및 **비상대응 가이드(Emergency Response)**

## 🚀 시작하기

### 실행 방법 (Docker)
1. 저장소 클론 및 이동:
   ```bash
   git clone https://github.com/tanminkwan/kdb_mw.git
   cd kdb_mw/mw_app
   ```
2. 컨테이너 실행 (Supervisor & Gunicorn 자동 구성):
   ```bash
   docker-compose up -d --build
   ```
3. 초기 DB 마이그레이션 및 관리자 계정 생성:
   ```bash
   docker exec -it mwm-app flask fab create-admin
   ```

## 🛠️ 유지보수 및 진단
- **비상 대응**: `docs/emergency_response.md`를 참조하여 DB 세션 정리 및 컨테이너 복구 절차 확인.
- **로그 모니터링**: 
  ```bash
  docker logs -f mwm-app
  ```

---

<p align="center">
  <b>리발소 - 효율적인 미들웨어 관리를 위한 최고의 선택</b><br>
  © 2026 MWM Team. All rights reserved.
</p>
