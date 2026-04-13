# SPEC_019: IDP OAuth2 Client Credentials Grant Type 지원

> **날짜**: 2026-04-13  
> **버전**: `CLIENT_CREDS(VER:20260413.002)`  
> **변경 요약**: IDP의 기존 사용자(`idp_user`) 모델과 `api_key` 메커니즘을 활용하여, 별도 테이블이나 모델 추가 없이 OAuth 2.0 `client_credentials` Grant Type을 지원한다.

---

## 1. 배경 및 필요성

- 현재 IDP는 `authorization_code` + `refresh_token` Grant Type만 지원하며, 모든 토큰 발급에 **사용자(User)의 브라우저 로그인**이 필수임.
- **문제점**:
  - 스케줄러, 백엔드 데몬, 외부 시스템 등 **UI 없이 API를 호출**해야 하는 시나리오를 지원할 수 없음.
- **해결책**:
  - 기존 `idp_user`의 `username`을 `client_id`로, `api_key`를 `client_secret`으로 활용하여 `client_credentials` 방식을 구현한다.
  - 신규 테이블, 신규 모델 없이 기존 인프라를 **100% 재활용**한다.

---

## 2. 핵심 설계 원리

### 2.1. 기존 자원 재활용 매핑

| OAuth2 개념 | 매핑 대상 | 비고 |
|------------|----------|------|
| `client_id` | `idp_user.username` | 기존 필드 |
| `client_secret` | `idp_user.api_key` | 기존 필드 (`mwm_sk_` 접두사) |
| 토큰 저장 | `oauth2_token` 테이블 | 기존 테이블 (`user_id` 활용) |
| 권한 | `idp_user.roles` → App의 Shadow User Role | 기존 동기화 체계 활용 |

### 2.2. 자연스러운 보안 게이트

`api_key`가 `nullable`이므로, **api_key가 발급된 사용자만** `client_credentials`를 사용할 수 있다.

- `api_key`는 IDP 대시보드에서 **Admin/PowerUser 권한을 가진 사용자만** 발급 가능 (기존 `/api-key/rotate` 엔드포인트)
- `api_key`가 NULL인 사용자 → `client_credentials` 인증 불가
- `active=false`인 사용자 → 인증 거부

### 2.3. API Key 직접 사용과의 차이

`api_key`는 현재 IDP 관리 API에서 Bearer 토큰으로 **직접 사용**되고 있다. `client_credentials`는 같은 `api_key`를 사용하지만 **프로토콜과 용도가 다르다**.

| | API Key (기존, 직접 사용) | Client Credentials (신규, 토큰 교환) |
|---|---|---|
| **인증 대상** | IDP 관리 API (`/api/users`, `/api/sync` 등) | App API (`/api/v1/was/list` 등 외부 리소스) |
| **방식** | `api_key`를 `Authorization: Bearer` 헤더에 **직접** 전송 | `username` + `api_key`로 OAuth2 **토큰을 발급**받아 사용 |
| **유효 기간** | `api_key`가 변경될 때까지 **영구** | 토큰 만료(`expires_in`, 기본 3600초)까지만 유효 |
| **매 요청 시** | 매번 `api_key` 원문 전송 | 발급받은 토큰만 전송 (원문 `api_key` 노출 최소화) |
| **App 호환성** | App의 OAuth2 기반 인증 체계와 **비호환** | App의 기존 인증 흐름과 **100% 호환** |

> **요약**: `api_key`는 IDP 내부 관리용, `client_credentials`는 **외부 시스템(App 등)의 자원에 접근**하기 위해 `api_key`를 OAuth2 토큰으로 교환하는 표준 절차이다. 두 방식은 공존한다.

---

## 3. 사용자 유형 가이드 (User Type Guide)

### ⚠️ 중요: IDP의 `idp_user`에는 두 가지 유형의 계정이 혼재한다

IDP의 `idp_user` 테이블에는 **실제 사람(Human User)**과 **시스템 계정(Service Account)**이 함께 존재할 수 있다. 이 두 유형은 동일한 테이블과 동일한 필드를 사용하지만, **용도와 운영 방식이 다르므로** 관리자는 이를 명확히 구분하여 운영해야 한다.

| 구분 | 사람 (Human User) | 시스템 (Service Account) |
|------|-------------------|------------------------|
| **예시** | `hong_gildong`, `kim_admin` | `api_collector_01`, `batch_worker` |
| **생성 방법** | App에서 생성 후 IDP로 동기화 | App에서 Shadow User로 수동 생성 후 IDP로 동기화 |
| **인증 방식** | 브라우저 로그인 (OIDC) | `client_credentials` (API 호출) |
| **패스워드** | 실제 로그인용 패스워드 사용 | 의미 없음 (임의 값 설정) |
| **api_key** | 선택 사항 | **필수** (client_secret으로 사용됨) |
| **용도** | 웹 UI 접속, 대시보드 조회 | 서버 간 API 호출, 자동화 스크립트 |

### 3.1. 네이밍 컨벤션 (권장)

시스템 계정은 사람 계정과 혼동되지 않도록 **접두사 규칙**을 적용하는 것을 권장한다.

| 유형 | 네이밍 예시 | 설명 |
|------|-----------|------|
| 사람 | `hong_gildong` | 실제 사용자 ID |
| 시스템 | `svc_collector`, `svc_batch_worker` | `svc_` 접두사로 시스템임을 명시 |

### 3.2. 운영 주의사항

- **시스템 계정으로 브라우저 로그인하지 말 것**: 기술적으로는 가능하지만, 감사(Audit) 로그에서 사람의 행위와 시스템의 행위가 구분되지 않게 된다.
- **사람 계정에 api_key를 발급하지 말 것 (원칙)**: 사람 계정에도 api_key를 발급하면 `client_credentials`로 사용할 수 있지만, 패스워드와 api_key가 동시에 존재하면 인증 경로가 이중화되어 보안 관리가 복잡해진다. 불가피한 경우가 아니면 시스템 계정에만 api_key를 발급한다.

---

## 4. 상세 설계 (Detailed Design)

### 4.1. 토큰 발급 로직 (`idp/app/services/oauth_service.py`)

`OAuthService` 클래스에 신규 메서드를 **추가**한다. 기존 메서드는 수정하지 않는다.

```python
def exchange_client_credentials_for_token(self, client_id, client_secret):
    """
    Client Credentials Grant Type 토큰 발급.
    client_id = idp_user.username, client_secret = idp_user.api_key
    
    검증 순서:
    1. username으로 idp_user 조회
    2. 사용자 활성 상태 확인 (active)
    3. api_key 일치 여부 확인
    
    기존 OAuth2Token 테이블에 저장하므로 별도 모델 불필요.
    """
    user = self.user_repo.get_by_username(client_id)
    if not user:
        raise ValueError("Invalid client_id")
    if not user.is_active:
        raise ValueError("User account is inactive")
    if not user.api_key or user.api_key != client_secret:
        raise ValueError("Invalid client_secret")
    
    expires_in = current_app.config["OAUTH2_TOKEN_EXPIRES_IN"]
    # NOTE: client_id 파라미터에는 OAuth2Client.client_id가 아닌
    # idp_user.username을 전달한다. create_token 내부에서 이 값을
    # 어떻게 사용하는지 확인 필요 (기존 동작에 영향이 없어야 함).
    token = self.oauth_repo.create_token(
        user_id=user.id,
        client_id=client_id,
        scope="openid profile email",
        expires_in=expires_in,
    )
    self.oauth_repo.commit()
    
    logger.info(f"Client credentials token issued for user={client_id}")
    return token.to_dict()
```

### 4.2. 엔드포인트 확장 (`idp/app/routes.py`)

`/oauth/token` 라우트의 기존 `else` 분기 앞에 `elif`를 **추가**한다.

```python
# 기존 authorization_code, refresh_token 분기는 그대로 유지
elif grant_type == "client_credentials":
    token_data = oauth_service.exchange_client_credentials_for_token(
        client_id=client_id,
        client_secret=client_secret,
    )
```

> **⚠️ 기존 함수 수정이 불가피한 이유**: OAuth 2.0 표준(RFC 6749 §3.2)은 토큰 발급을 **단일 엔드포인트(`/oauth/token`)**에서 `grant_type` 파라미터로 분기 처리하도록 규정하고 있다. 별도 엔드포인트(예: `/oauth/token-client`)를 만들면 표준을 위반하여 클라이언트 라이브러리(Authlib 등)와의 호환성이 깨진다. 따라서 기존 `token()` 함수에 `elif` 분기를 추가하는 것은 **불가피**하며, 이때 기존 `authorization_code` 분기, `refresh_token` 분기, `else` 에러 반환 로직은 **일절 수정하지 않는다**.

### 4.3. 기존 코드 변경 없음 확인

| 파일 | 변경 여부 | 설명 |
|------|----------|------|
| `idp/app/models.py` | ❌ 변경 없음 | 신규 테이블/모델 불필요 |
| `idp/app/repositories/oauth_repo.py` | ❌ 변경 없음 | 기존 `create_token` 메서드 재활용 |
| `idp/app/repositories/user_repo.py` | ❌ 변경 없음 | 기존 `get_by_username` 메서드 재활용 |
| `idp/app/api.py` | ❌ 변경 없음 | 기존 `/api/userinfo` 그대로 동작 |
| `idp/app/templates/*` | ❌ 기존 템플릿 변경 없음 | 기존 UI 수정 불필요 (단, 신규 `admin_credentials.html` 추가) |
| App 전체 | ❌ 변경 없음 | 토큰에 `user_id`가 있으므로 기존 인증 로직 그대로 동작 |

---

## 5. Application 측 연동

### 5.1. App 코드 변경이 불필요한 이유

`client_credentials`로 발급된 토큰도 기존 `OAuth2Token` 테이블에 `user_id`와 함께 저장된다. 따라서:

1. App이 토큰으로 `/api/userinfo`를 호출하면 → **기존과 동일하게** 사용자 정보(username, email, roles)가 반환된다.
2. App은 이 사용자 정보로 기존 RBAC 로직을 적용한다.
3. 즉, App 입장에서는 OIDC 로그인으로 받은 토큰이든 `client_credentials`로 받은 토큰이든 **구분할 필요가 없다**.

### 5.2. Credential 발급 절차 (관리자 작업)

`client_credentials`에 필요한 Credential은 다음 두 가지이다:

| Credential | 값 | 출처 |
|------------|---|------|
| `client_id` | `idp_user.username` | App에서 Shadow User 생성 → IDP 동기화 시 자동 결정 |
| `client_secret` | `idp_user.api_key` | **관리자가 IDP에서 발급** |

즉, 관리자가 해야 할 일은 **해당 유저에게 api_key를 발급해 주는 것**이다. 이것이 곧 `client_secret`이 된다.

#### 현재 문제점

현재 IDP의 `/api-key/rotate`는 **본인 계정의 api_key만 발급**하는 구조이다. 시스템 계정(Service Account)은 브라우저로 IDP에 직접 로그인하는 것이 부자연스러우므로, 관리자가 대신 발급해 줄 수 있어야 한다.

#### 해결: 신규 관리 페이지 추가 (기존 코드 수정 없음)

기존 코드(`/api-key/rotate`, `/admin/settings` 등)는 **일절 수정하지 않고**, 완전히 새로운 라우트와 UI를 추가한다.

- **신규 라우트**: `GET /admin/credentials` — Credential 관리 페이지 표시
- **신규 라우트**: `POST /admin/credentials/<user_id>/issue` — 지정한 사용자의 api_key 생성/회전
- **신규 UI**: `idp/app/templates/admin_credentials.html` — 사용자 목록에서 Credential(api_key) 발급/회전 버튼을 제공하는 **별도 관리 페이지**

#### 관리자 화면 구성 및 조작 흐름

**1단계: 관리자가 IDP 메뉴에서 "Credential 관리" 클릭** → `/admin/credentials` 페이지 이동

**2단계: 사용자 목록에서 대상 유저 확인**

```
┌─────────────────────────────────────────────────────────────┐
│  Client Credentials 관리                                     │
├──────────────┬───────────┬──────────────────┬───────────────┤
│ Username     │ Roles     │ Client Secret    │ 작업          │
├──────────────┼───────────┼──────────────────┼───────────────┤
│ svc_collector│ [Admin]   │ mwm_sk_xR7kL9... │ [재발급]      │
│ svc_batch    │ [PowerU.] │ (미발급)          │ [발급]        │
│ hong_gildong │ [Admin]   │ mwm_sk_aB2pQ4... │ [재발급]      │
└──────────────┴───────────┴──────────────────┴───────────────┘
```

**3단계: 대상 유저의 [발급] 또는 [재발급] 버튼 클릭**
- `POST /admin/credentials/<user_id>/issue` 호출
- 확인 다이얼로그: "svc_batch의 Client Secret을 발급하시겠습니까?"

**4단계: 발급 완료 후 결과 표시**
```
✅ Credential 발급 완료
  client_id:     svc_batch
  client_secret: mwm_sk_nEw7kEy9sEcReT...
  ⚠️ 이 값은 다시 조회할 수 없습니다. 지금 복사하세요.
```

### 5.3. 전체 운영 절차 (End-to-End)

**① App 사용자 관리 화면**에서 Shadow User 생성 (`svc_collector`, Role: Admin)

**② IDP 관리 화면**에서 "동기화" 실행 → `svc_collector`가 `idp_user`에 등록됨

**③ IDP `/admin/credentials` 화면**에서 `svc_collector`의 [발급] 버튼 클릭 → `api_key` 생성됨

**④ 관리자가 운영자에게 Credential 전달**:
```
client_id:     svc_collector
client_secret: mwm_sk_xR7kL9...
```

**⑤ 클라이언트 시스템**에서 `/oauth/token` API로 토큰 발급:
```bash
curl -X POST http://idp-server:5000/oauth/token \
     -d "grant_type=client_credentials" \
     -d "client_id=svc_collector" \
     -d "client_secret=mwm_sk_xR7kL9..."
```

**⑥ 클라이언트 시스템**에서 발급된 토큰으로 App API 호출:
```bash
curl -X GET http://mw-app:8000/api/v1/was/list \
     -H "Authorization: Bearer <access_token>"
```

---

## 6. 보안 고려사항 (Security)

| 항목 | 정책 |
|------|------|
| **api_key 관리** | 환경변수로 주입. 코드 내 하드코딩 금지. 주기적 Rotation 권장 (Credential 관리 페이지 `/admin/credentials` 에서 [재발급]) |
| **Refresh Token** | `client_credentials`에서는 **발급됨** (기존 `create_token` 재활용). 필요 시 Refresh Token 제외 로직 추가 가능 |
| **HTTPS** | 운영 환경에서는 HTTPS 필수 (api_key가 평문 전송되므로) |
| **비활성 계정 차단** | `active=false`인 사용자는 토큰 발급 거부 |
| **감사 로그** | 토큰 발급 시 `username`과 요청 IP를 로깅하여 추적 가능 |
| **계정 분리** | 시스템 계정과 사람 계정을 네이밍으로 구분 (§3.1 참조) |

---

## 7. 기존 기능 영향도 분석 (Impact Analysis)

### 7.1. 영향 없음 (Safe - 추가만 하는 변경)

| 변경 대상 | 이유 |
|----------|------|
| `OAuthService`에 메서드 추가 | 기존 메서드 수정 없음. **신규 메서드만 추가** |
| `/oauth/token` 라우트에 `elif` 분기 추가 | 기존 `authorization_code`, `refresh_token` 분기 그대로 유지 |
| `/admin/credentials` 신규 라우트 + UI 추가 | 완전 **신규 라우트 및 신규 템플릿**이므로 기존 코드에 영향 없음 |

### 7.2. 영향 없음 확인 체크리스트

구현 완료 후 반드시 다음을 확인한다:

- [ ] 기존 OIDC 로그인 흐름(mwm-app → IDP → callback) 정상 동작
- [ ] 기존 `authorization_code` 토큰 발급 정상 동작
- [ ] 기존 `refresh_token` 갱신 정상 동작
- [ ] 기존 `/api/userinfo` 정상 동작
- [ ] 기존 IDP 유닛 테스트 전체 통과 (`pytest idp/tests/`)

---

## 8. 단계별 구현 계획 (Implementation Roadmap)

### Phase 0: 선행 요건 — Credential 관리 페이지 (신규 라우트 + 신규 UI)
1. `GET /admin/credentials` 신규 라우트 구현 (사용자 목록 + api_key 상태 표시)
2. `POST /admin/credentials/<user_id>/issue` 신규 라우트 구현 (api_key 생성/회전)
3. `admin_credentials.html` 신규 템플릿 작성
4. 해당 기능의 유닛 테스트 작성

### Phase 1: IDP 토큰 발급 로직 추가
1. `OAuthService`에 `exchange_client_credentials_for_token` 메서드 추가
2. `/oauth/token` 라우트에 `client_credentials` 분기 추가
3. 유닛 테스트 작성 및 검증
4. **기존 테스트 전체 실행하여 Regression 없음 확인**

### Phase 2: 연동 테스트
1. App에 Shadow User(`svc_test`) 생성 및 Role 부여
2. IDP 동기화 실행
3. 관리자가 해당 유저의 api_key 대리 발급
4. `client_credentials` 토큰 발급 → App API 호출 E2E 테스트

---

## 9. 수정 대상 파일 목록

| 구분 | 파일 | 변경 내용 |
|------|------|----------|
| IDP 신규 (Phase 0) | `idp/app/routes.py` | `GET /admin/credentials`, `POST /admin/credentials/<user_id>/issue` 신규 라우트 추가 |
| IDP 신규 (Phase 0) | `idp/app/templates/admin_credentials.html` | Credential 관리 전용 UI 페이지 신규 |
| IDP 변경 (Phase 1) | `idp/app/services/oauth_service.py` | `exchange_client_credentials_for_token` 메서드 추가 |
| IDP 변경 (Phase 1) | `idp/app/routes.py` | `/oauth/token`에 `elif client_credentials` 분기 추가 |
| IDP 신규 | `idp/tests/test_client_credentials.py` | Client Credentials 전용 테스트 케이스 |

> 기존 모델, 기존 UI 템플릿, App 코드 변경 없음.

---

## 10. 테스트 케이스

| # | 테스트 시나리오 | 기대 결과 |
|---|---------------|----------|
| 1 | 유효한 `username`/`api_key`로 `client_credentials` 토큰 요청 | 200, `access_token` 반환 |
| 2 | 잘못된 `api_key`로 토큰 요청 | 400, `Invalid client_secret` |
| 3 | `api_key`가 NULL인 사용자로 토큰 요청 | 400, `Invalid client_secret` |
| 4 | 존재하지 않는 `username`으로 요청 | 400, `Invalid client_id` |
| 5 | `active=false`인 사용자로 요청 | 400, `User account is inactive` |
| 6 | Basic Auth 헤더 방식으로 자격 증명 전달 | 200, 정상 토큰 발급 |
| 7 | 발급된 토큰으로 `/api/userinfo` 호출 | 200, 해당 사용자 정보 반환 |
| 8 | 기존 `authorization_code` 흐름이 여전히 정상 동작 | 200, 기존과 동일 |
| 9 | Credential 관리 페이지: 관리자가 특정 유저의 api_key 발급 | 200, `mwm_sk_` 접두사의 키 생성 |
| 10 | Credential 관리 페이지: 비관리자(일반 유저)가 접근 | 403 또는 로그인 리다이렉트 |
| 11 | Credential 관리 페이지: 이미 발급된 유저에 재발급 | 200, 기존 키 대체, 새 키 반환 |

---

## 11. 사용 시뮬레이션 (Example Usage)

### 11.1. 사전 준비 (관리자 작업)

```
[App 사용자 관리 화면]
  1. Shadow User 추가:
     - Username: svc_collector
     - Password: (임의 값)
     - Role:     Admin

[IDP 관리 화면]
  2. "동기화" 버튼 클릭
     → svc_collector가 idp_user에 등록됨

[IDP Credential 관리 페이지 (/admin/credentials)]
  3. svc_collector 행의 [발급] 버튼 클릭
     → mwm_sk_xR7kL9... 형태의 Client Secret 생성됨
     → 화면에 표시된 값을 복사하여 운영자에게 전달
```

### 11.2. 토큰 발급 요청 (Client → IDP)

```bash
# Basic Auth 방식 (권장)
curl -X POST http://idp-server:5000/oauth/token \
     -u "svc_collector:mwm_sk_xR7kL9..." \
     -d "grant_type=client_credentials"

# POST Body 방식
curl -X POST http://idp-server:5000/oauth/token \
     -d "grant_type=client_credentials" \
     -d "client_id=svc_collector" \
     -d "client_secret=mwm_sk_xR7kL9..."
```

**응답 예시**:
```json
{
    "access_token": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
    "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "openid profile email"
}
```

### 11.3. 자원 접근 요청 (Client → App API)

```bash
curl -X GET http://mw-app:8000/api/v1/was/list \
     -H "Authorization: Bearer dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
```

### 11.4. 내부 처리 흐름

```
1. App이 Bearer 토큰으로 IDP의 /api/userinfo 호출
2. IDP가 OAuth2Token 테이블에서 토큰 조회 → user_id 확인
3. 해당 user_id의 사용자 정보(username, roles) 반환
   → {"username": "svc_collector", "roles": ["Admin"], ...}
4. App은 기존 로직과 동일하게 사용자 권한 확인 후 API 응답
```

> **핵심**: App 입장에서는 OIDC 로그인으로 받은 토큰이든 `client_credentials`로 받은 토큰이든 **완전히 동일하게 처리**된다. 구분할 필요가 없다.

### 11.5. 클라이언트 자격 증명 관리 가이드 (Best Practice)

각 클라이언트 App이나 스크립트에서 Credential을 안전하게 관리하기 위해 다음과 같은 방식을 권장한다.

#### 1) Credential 파일 사용 (`.mwm-credential`)
클라이언트 실행 경로 또는 홈 디렉토리에 JSON 형식으로 저장한다.

**파일명**: `.mwm-credential` (숨김 파일)
```json
{
    "client_id": "svc_collector",
    "client_secret": "mwm_sk_xR7kL9..."
}
```

#### 2) 보안 권한 설정
비밀키 노출 방지를 위해 파일 권한을 소유자 전용으로 제한한다.
```bash
chmod 600 .mwm-credential
```

#### 3) Git 관리 주의
실수로 소스 코드 저장소에 업로드되지 않도록 `.gitignore`에 반드시 등록한다.

#### 4) 구현 예시 (Python)
환경 변수를 우선 조회하고, 없을 경우 파일을 읽는 방식이 가장 유연하다.

```python
import os
import json

def load_credentials():
    # 1. 환경 변수 우선 조회
    cid = os.getenv("MWM_CLIENT_ID")
    secret = os.getenv("MWM_CLIENT_SECRET")
    
    if cid and secret:
        return cid, secret
        
    # 2. 파일에서 조회
    cred_path = ".mwm-credential"
    if os.path.exists(cred_path):
        with open(cred_path, "r") as f:
            data = json.load(f)
            return data.get("client_id"), data.get("client_secret")
            
    raise Exception("Credential missing (Env or .mwm-credential)")
```

---

## 12. 주의 사항

- **api_key 발급 절차**: 현재 api_key 자가 발급(`/api-key/rotate`)은 본인 계정에 대해서만 가능하며, Admin/PowerUser 권한이 필요하다. 시스템 계정은 이 권한이 없을 수 있으므로, **관리자가 대리 발급하는 기능이 선행 구현되어야 한다** (§5.2 참조).
- **시간 동기화**: 토큰 만료 검증을 위해 IDP 서버와 App 서버 간 NTP 동기화가 필수적이다.
- **기존 API Key 인증과의 관계**: IDP의 관리용 API(`/api/users`, `/api/sync` 등)는 `api_key`를 Bearer 토큰으로 직접 사용하는 방식이다. `client_credentials`는 `api_key`를 **OAuth2 토큰을 발급받기 위한 수단**으로 사용하므로 용도가 다르다. 두 방식은 공존 가능하다.
