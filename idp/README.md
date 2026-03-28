# MWM IDP (Identity Provider)

이 폴더는 **MWM OAuth2 Identity Provider (IDP)** 서버의 독립적인 소스 코드 및 설정을 포함합니다.

## 프로젝트 구조

```text
idp/
├── app/                  # Flask 애플리케이션 소스 코드 (Core)
│   ├── __init__.py      # App Factory
│   ├── config.py         # 설정 (DB, Authlib, Sync 등)
│   ├── models.py         # DB 모델 (IdpUser, OAuth2Client 등)
│   ├── routes.py         # OAuth2 엔드포인트 및 로그인 UI
│   ├── api.py            # REST API (Userinfo, Sync 등)
│   ├── run.py            # 서버 진입점
│   ├── repositories/     # 데이터 접근 계층 (SOLID: DIP)
│   ├── services/         # 비즈니스 로직 계층 (SOLID: SRP)
│   └── templates/        # UI 템플릿
├── tests/                # pytest 기반 단위/통합 테스트
├── Dockerfile.idp        # IDP 컨테이너 빌드 정의
├── create_idp_db.sql     # IDP 전용 데이터베이스 초기화 SQL
└── requirements.txt      # Python 의존성 목록
```

## 주요 기능

- **OAuth2 Authorization Server**: `authorization_code` 및 `refresh_token` Grant Type 지원 (Authlib 기반).
- **Session-Based SSO**: `Flask-Login`을 통한 세션 관리로 멀티 클라이언트 로그인 지원.
- **범용 외부 DB 동기화**: `mwm-app` 등 외부 시스템의 사용자 정보를 자체 DB로 동기화.
- **REST API**: 사용자 정보 조회 (`/api/userinfo`) 및 동기화 제어.

## 로컬 개발 및 실행 (Local Development)

### 1. 환경 변수 설정
`idp/app/config.py`를 참조하거나 다음 환경 변수를 설정하십시오:
- `IDP_DATABASE_URI`: PostgreSQL 접속 URI
- `IDP_SECRET_KEY`: Flask 세션 및 CSRF 보호용 키
- `SYNC_MWM_DB_URI`: 동기화 대상 DB 접속 URI

### 2. 가상환경 및 의존성 설치
```bash
cd idp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 서버 실행
```bash
export PYTHONPATH=.
python app/run.py
```

## 테스트 실행 (Testing)

`pytest`를 사용하여 테스트를 실행할 수 있습니다. `idp/` 디렉터리 내에서 실행하십시오.

```bash
cd idp
pytest tests/
```

## Docker 빌드 및 실행

전체 시스템(`mw_app`)의 `docker-compose.yml`을 통해 실행하는 것을 권장합니다.

```bash
# 전체 실행 시
docker compose up -d mwm-idp

# IDP만 빌드 시
docker compose build mwm-idp
```
