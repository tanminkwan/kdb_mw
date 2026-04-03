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

### 🛡️ 데이터 정합성 & 보안 강화
- **통합 인증 체계**: OIDC/OAuth2 기반의 SSO 및 **개인 인증 토큰(JWT)** 발급 시스템 구축.
- **API 보안**: 외부 툴 연동을 위한 1년(365일) 유효 장기 토큰 관리 기능 (`나의 정보` 메뉴).
- **Host ID 표준화**: 시스템 전반의 `host_id`를 소문자로 강제 통일하여 장애 원천 차단.
- **지식정보 그룹 권한**: Role 기반 접근제어(UtKmGroup)를 통한 콘텐츠 보안 강화.

### 📧 고급 리포팅 & API 연동
- **Smart Email API (Markdown/HTML)**:
  - **Mermaid 다이어그램**: 본문에 포함된 Mermaid 코드를 이미지로 자동 렌더링하여 삽입.
  - **S3 이미지 인라인**: 오브젝트 스토리지(MinIO) 링크를 감지하여 본문 내장(CID) 이미지로 자동 변환.
- **협업 최적화**: Select2 기반의 유연한 수신자 선택 및 Markdown 기반 지식베이스 구축.

## 🏗️ 시스템 아키텍처

- **Backend**: Python 3.12, Flask 2.2+, Flask-AppBuilder
- **Persistent Scheduler**: 
  - **SQLAlchemyJobStore** 도입으로 스케줄 정보 DB 영구 저장.
  - Multi-Worker(Gunicorn) 환경에서도 안전한 단일 스케줄러 인스턴스 보장.
- **Storage/Cache**: PostgreSQL 16+, Redis 7+ (Session & Cache)
- **Engine 연동**: Kroki (Mermaid 렌더링), MinIO/S3 (오브젝트 스토리지)

## 📂 주요 가이드 (Documentation)
- **[Email API 연동 가이드 (초보용)](docs/HOWTO_010_email_api_guide.md)**: 토큰 발급부터 Python 연동 샘플까지 포함.
- **[비상 대응 가이드 (Emergency Response)](docs/emergency_response.md)**: DB 세션 정리 및 컨테이너 복구 절차.
- **[OAuth2 & OIDC 연동 가이드](idp/README.md)**: IDP 서버 구성 및 SSO 설정.

## 🚀 시작하기

### 실행 방법 (Docker)
1. 저장소 클론 및 이동:
   ```bash
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
- **로그 모니터링**: 
  ```bash
  docker logs -f mwm-app
  ```

---

<p align="center">
  <b>리발소 - 효율적인 미들웨어 관리를 위한 최고의 선택</b><br>
  © 2026 MWM Team. All rights reserved.
</p>
