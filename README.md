# 🛠️ MWM (Middleware Management System) - 리발소

<p align="center">
  <img src="app/static/img/mwm_banner.png" alt="MWM Banner" width="800">
</p>

## 📋 프로젝트 개요
**리발소(리포트 발송 소형 엔진)**는 미들웨어(WAS, WEB) 및 IT 자산의 상태를 모니터링하고, 변경 사항을 대사(Compare)하며, Kroki 기반의 Mermaid 다이어그램을 포함한 고급 이메일 리포트를 생성하는 통합 관리 솔루션입니다.

## ✨ 주요 기능
- **미들웨어 모니터링**: JEUS, WebToB 등 주요 미들웨어 인스턴스 상태 추적
- **ITAM 데이터 대사**: 운영 환경과 ITAM(자산 관리 시스템) 간의 불일치 데이터 자동 탐지 및 보고
- **지식정보 관리 (HTML / Markdown)**:
  - 콘텐츠 조회 페이지에서 **이메일 발송** (Select2 태그 선택 + 직접 입력)
  - **그룹 기반 접근제어**: Role별 공개그룹 지정, 본인 작성 콘텐츠는 권한 무관 열람
  - 작성자 ID·이름 목록 표시
  - `지식유형-` 태그 기반 분류 체계
- **고급 리포팅**: 
  - Markdown 기반 문서 작성 및 관리
  - **Mermaid.js** 다이어그램 지원 (Kroki 엔진 연동)
  - 이메일 발송 시 다이어그램을 이미지로 자동 변환하여 포함
- **오브젝트 스토리지 연동**: MinIO/S3를 통한 이미지 및 첨부 파일 관리
- **스케줄링**: 주기적인 데이터 수집 및 리포트 발송 자동화 (Flask-APScheduler)

## 🏗️ 기술 스택
- **Backend**: Python 3.12, Flask, Flask-AppBuilder
- **Database**: PostgreSQL (Main), Redis (Session/Cache)
- **Container**: Docker, Docker Compose
- **Monitoring/External**: Kroki (Diagrams), MinIO (Object Storage)
- **Process Management**: Gunicorn, Supervisor

## 📁 주요 아키텍처
- **app/views**: 비즈니스 로직 및 웹 인터페이스
- **app/models**: IT 자산 및 미들웨어 데이터 모델 (SQLAlchemy)
- **app/api**: 외부 연동 및 데이터 수집을 위한 RESTful API
- **app/sqls**: 대용량 데이터 처리를 위한 최적화된 SQL 쿼리 관리
- **MWM-App**: Gunicorn 서빙 및 Supervisor 관리

## 🚀 시작하기

### 요구 사항
- Docker & Docker Compose
- Python 3.12+ (로컬 개발 시)

### 실행 방법 (Docker)
1. 저장소 클론:
   ```bash
   git clone https://github.com/tanminkwan/kdb_mw.git
   cd kdb_mw/mw_app
   ```
2. 환경 변수 설정 (`.env` 파일 생성):
   ```env
   MWM_DATABASE_URI=postgresql://tiffanie:passwd@mwm-db:5432/mw
   REDIS_URL=redis://mwm-redis:6379/0
   # 기타 필요한 설정들 (SMTP, S3 등)
   ```
3. 컨테이너 실행:
   ```bash
   docker-compose up -d --build
   ```
4. 관리자 계정 생성:
   ```bash
   docker exec -it mwm-app flask fab create-admin
   ```

## ⚙️ 주요 설정 (config.py)
- `KROKI_URL`: 다이어그램 렌더링 서버 주소
- `AWS_URL`: MinIO/S3 오브젝트 스토리지 주소
- `KDB_SMTP_*`: 이메일 알림 발송을 위한 SMTP 설정

---

<p align="center">
  <b>리발소 - 효율적인 미들웨어 관리를 위한 최고의 선택</b><br>
  © 2026 MWM Team. All rights reserved.
</p>
