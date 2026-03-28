# MWM IDP (Identity Provider)

이 폴더는 **MWM OAuth2 & OIDC Identity Provider (IDP)** 서버의 독립적인 소스 코드 및 설정을 포함합니다.  
본 서비스는 `mwm-app`(시스템 관리 도구) 및 `mwm-minio`를 포함한 여러 클라이언트 애플리케이션에 고도화된 Single Sign-On(SSO) 환경을 제공합니다.

## 🚀 주요 기능 (Features)

- **OIDC (OpenID Connect) 지원**: (New) RS256 서명 기반 ID Token 발급, Discovery 엔드포인트 및 JWKS 지원.
- **REST API 보안 (API Key)**: (New) Bearer 토큰(mwm_sk_...) 기반의 관리자 전용 API 보안 레이어 구축.
- **통합 관리자 콘솔 (Admin Console)**: (New) `/admin/settings` 경로를 통한 클라이언트 관리, API Key 갱신, 사용자 조회 및 수동 동기화 통합 제어.
- **OAuth2 Authorization Server**: `authorization_code` 및 `refresh_token` Grant Type 지원 (Authlib 기반).
- **사용자 데이터 동기화 (Sync)**: `mwm-app` DB의 최신 정보를 수동/자동으로 가져오는 Pull 기반 동기화 서비스.
- **Session-Based SSO**: `Flask-Login`과 세션 관리를 통해 멀티 클라이언트 로그인 시 재로그인 불필요.

## 📁 프로젝트 구조 (Architecture)

```text
idp/
├── app/                  # Flask 애플리케이션 소스 코드 (Core)
│   ├── __init__.py      # App Factory & Blueprint 등록
│   ├── config.py         # 설정 (DB, OIDC, SyncSources 등)
│   ├── models.py         # DB 모델 (IdpUser, OAuth2Client, OAuth2Token)
│   ├── routes.py         # OAuth2/OIDC/Admin UI 핸들러
│   ├── api.py            # REST API (Userinfo, Sync, API Key 보안)
│   ├── run.py            # 서버 진입점 및 초기화 로직
│   ├── repositories/     # 데이터 접근 계층 (SOLID: DIP)
│   ├── services/         # 비즈니스 로직 및 동기화 전략 (SOLID: SRP/OCP)
│   └── templates/        # UI 템플릿 (Admin Console 포함)
├── tests/                # pytest 기반 단위/통합 테스트 (Pytest-Mock)
├── Dockerfile.idp        # IDP 전용 경량화 Docker 이미지 
├── create_idp_db.sql     # IDP 전용 PostgreSQL 초기화 SQL
└── requirements.txt      # Python 의존성 목록 (Authlib, Flask-Login 등)
```

## 🛠️ 관리 포인트 (Admin Operations)

### 1. 어드민 콘솔 (Admin Console)
- **주소**: [https://idp.mwm.local:20443/admin/settings](https://idp.mwm.local:20443/admin/settings)
- **대상**: `Admin` 또는 `PowerUser` 역할(Role)을 가진 사용자만 접근 가능.
- **기능**:
  - OAuth2 클라이언트 등록 및 MinIO OIDC 정책 매핑 (Policy Mapping).
  - 사용자별 REST API Key 발급/갱신 (Rotate Key).
  - 전체 사용자 목록 및 역할 정보 (Read-only) 모니터링.

### 2. REST API 보안 사용 (API Key)
관리자 전용 REST API 호출 시 헤더에 발급받은 API Key를 포함해야 합니다.
```bash
curl -k -X GET https://idp.mwm.local:20443/api/userinfo \
     -H "Authorization: Bearer <mwm_sk_your_key_here>"
```

### 3. 사용자 동기화 (Sync)
`mwm-app`에서 변경된 사용자/권한 정보를 즉시 반영하려면 어드민 콘솔의 **[Sync Now]** 버튼을 통해 동기화를 수행하십시오.

## 🧪 로컬 개발 환경 (Local Dev)

1. **환경 변수 설정**: `IDP_DATABASE_URI`, `SYNC_MWM_DB_URI`, `IDP_RSA_PRIVATE_KEY` 등을 설정합니다.
2. **패키지 설치**: `pip install -r requirements.txt`
3. **서버 실행**: `export PYTHONPATH=. && python app/run.py`
4. **테스트 수행**: `pytest tests/`

## 🐳 Docker 배포 가이드
전체 시스템(`mw_app`)의 루트 디렉터리에서 `docker-compose.yml`을 통해 관리됩니다. 소스 변경 시 반드시 재빌드 및 재시작이 필요합니다.
```bash
docker compose up -d --build --force-recreate mwm-idp
```

---
*본 문서는 2026-03-28 최종 업데이트 되었습니다.*
