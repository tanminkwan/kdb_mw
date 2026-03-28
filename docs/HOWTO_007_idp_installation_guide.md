# HOWTO 007 - MWM-IDP (인증 서버) 설치 및 운영 가이드

본 문서는 `mwm-idp` (OIDC/OAuth2 인증 서버)를 설치하고 운영 환경에 배포하기 위한 상세 절차를 기술합니다.

---

## 1. 개요 (Description)

`mwm-idp`는 `mwm-app`의 사용자 정보를 통합 관리하고, OAuth2/OIDC 표준을 통해 외부 시스템(MinIO, Kroki 등)에 Single Sign-On(SSO) 기능을 제공하는 독립 인증 서비스입니다.

---

## 2. 사전 요구 사항 (Prerequisites)

- **Docker & Docker Compose**: 컨테이너 환경에서 실행됩니다.
- **PostgreSQL**: `mwm-db` 내에 `idp` 전용 데이터베이스가 필요합니다.
- **SSL 인증서**: OIDC 통신은 HTTPS를 강력히 권고합니다. ([HOWTO 005](./HOWTO_005_generate_ssl_certificates.md) 참고)

---

## 3. Step 1: 데이터베이스 초기화 (Database Setup)

`mwm-idp`는 독립적인 DB(`idp`)를 사용합니다. 호스트에서 다음 명령을 통해 DB를 생성합니다.

```bash
# PostgreSQL 컨테이너에 접속하여 DB 생성 및 권한 부여
docker exec -it mwm-db psql -U postgres -c "CREATE DATABASE idp;"
docker exec -it mwm-db psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE idp TO tiffanie;"
docker exec -it mwm-db psql -U postgres -d idp -c "ALTER SCHEMA public OWNER TO tiffanie;"
```

---

## 4. Step 2: RS256 서명용 개인키 생성 (RSA Key Generation)

OIDC ID Token의 서명을 위해 2048비트 RSA 개인키가 필요합니다. 이 키는 `idp/app/config.py`의 기본값을 대체하여 운영 환경 변수로 주입되어야 합니다.

```bash
# 2048비트 RSA 개인키 생성
openssl genrsa -out idp_private.pem 2048

# PEM 포맷 확인 (이 내용을 복사하여 환경변수에 주입합니다)
cat idp_private.pem
```

> [!IMPORTANT]
> 개인키는 절대 외부에 노출되어서는 안 되며, `docker-compose.yml` 등에 직접 기입 시 개행 문자(`\n`)를 포함한 한 줄 문자열로 변환하여 처리해야 합니다.

---

## 5. Step 3: 환경 변수 구성 (Full Configuration Guide)

`mwm-idp`의 모든 거동은 환경변수를 통해 제어됩니다. 운영 환경에서 실수하기 쉬운 핵심 설정들을 아래와 같이 `docker-compose.yml`에 상세히 정의해야 합니다.

### 5-1. 환경변수 상세 정의 (Environment Variables)

| 카테고리 | 환경변수명 | 설명 | 비고 |
|:--- |:--- |:--- |:--- |
| **DB** | `IDP_DATABASE_URI` | IDP 전용 DB 접속 URI | `postgresql://.../idp` |
| **보안** | `IDP_SECRET_KEY` | Flask 세션 및 CSRF 보안용 비밀키 | 복잡한 문자열 권장 |
| | `IDP_PASSWORD_MIN_LENGTH` | 사용자 암호 최소 길이 (기본: 8) | |
| **OAuth2** | `OAUTH2_TOKEN_EXPIRES_IN` | Access Token 유효 기간 (초) | 기본: 3600 (1시간) |
| | `OAUTH2_REFRESH_TOKEN_EXPIRES_IN` | Refresh Token 유효 기간 (초) | 기본: 86400 (24시간) |
| **OIDC** | `OIDC_ISSUER` | 토큰 내 발행자 식별 URL | 브라우저 접근 주소와 일치 필수 |
| | `IDP_RSA_PRIVATE_KEY` | RS256 서명용 RSA 개인키 (PEM) | Step 2에서 생성한 값 |
| **클라이언트**| `IDP_MWM_CLIENT_ID` | 기본 클라이언트(`mwm-app`) ID | |
| | `IDP_MWM_CLIENT_SECRET` | 기본 클라이언트 비밀번호 | |
| | `IDP_MWM_REDIRECT_URI` | 인증 후 돌아갈 주소 (Callback) | |
| **운영** | `IDP_EXTERNAL_SERVER_URL` | 외부 접근용 Base URL | `https://idp.mwm.local...` |
| | `IDP_APP_TITLE` | 화면에 표시될 서비스 명칭 | |
| | `IDP_LOG_LEVEL` | 로그 상세도 (INFO, DEBUG 등) | |
| **동기화** | `SYNC_MWM_DB_URI` | `mwm-app` 사용자를 가져올 DB 주소 | |

### 5-2. `docker-compose.yml` 전체 예시

아래 내용을 복사하여 운영 환경에 맞게 수정하십시오. 특히 개행이 포함된 **RSA 개인키** 입력 방식에 유의하십시오.

```yaml
  mwm-idp:
    container_name: mwm-idp
    image: mwm-idp
    build:
      context: ./idp
      dockerfile: Dockerfile.idp
    ports:
      - "5000:5000"
    environment:
      # [필수] 로컬 타임존 설정
      - TZ=Asia/Seoul
      
      # [필수] 데이터베이스 접속 정보
      - IDP_DATABASE_URI=postgresql://tiffanie:1q2w3e4r!!@mwm-db:5432/idp
      - SYNC_MWM_DB_URI=postgresql://tiffanie:1q2w3e4r!!@mwm-db:5432/mw
      
      # [중요] 보안 및 세션 설정
      - IDP_SECRET_KEY=y0ur-v3ry-compl3x-s3cret-k3y
      - IDP_APP_TITLE=MWM Identity Provider (PROD)
      
      # [중요] OIDC 발행자 정보 (브라우저가 접근하는 주소와 동일해야 함)
      - OIDC_ISSUER=https://idp.mwm.local:20443
      - IDP_EXTERNAL_SERVER_URL=https://idp.mwm.local:20443
      
      # [필수] RS256 서명용 개인키
      # 주의: PEM 파일 내용을 그대로 붙여넣되, 따옴표 없이 \n으로 개행을 표시하거나
      # 아래와 같이 YAML 블록 구문(|)을 사용하여 원본 포맷을 유지할 수도 있습니다.
      - IDP_RSA_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIIEugIBADANBgkqhkiG9w0BAQEFAASCBKQwggSgAgEAAoIBAQC8leDKAXXLSXMg\n5+w/chxXcVqxQHhWQsyOcUGovVcdi5Qgh+cHqAtOgwE/UlfnOI/6nUfnahYHIPVI\neOCiSzQiFJe2TKqs4eHEduaSKa1wrqlrzBNv282UHin9xQ280x2kztzMHuZYoUSu\nKmVUMCZ2OXbDEctNSexNcYVF62PlcJfJ65TDuXry4V0YPcrxELCBhCURc9RUfrQX\nv9sWK7n0I0dgbGa5/IfY0MUNjE+5zCgMtwjiC9rDyDfhfqdwtWgCLHkfZzTtXW6E\nc51L45KbPaxoM/ujQ7+jiS+PlDm48RQgeVDJNNX0uQEH3/ewlTS73wpqH+L60lUF\nruM/46D7AgMBAAECgf8Ynoy4AzO06palNRekffX8V/ahktM3OtqiL6jy9tEZZb/q\np+ur6YtXcYXexHmUzFGeBpURUbXbrjrxsv682+O7k1IafH4c2tYaZC5kYF3ILXbo\nkZUs1nr17YRU+D4V7J5FZbgD0WJVP/2EjnINjZkebF3+Yn75QLNl4rc4Lp0fB3Dg\nwfX+DWvl81o9ffUh0t/ltvCo64TSzJHBeNHU32gNrjbBlGQoU/J7kVHv5/0egDrm\nIYFfa9DNfknRTwPPZQwX6pf9xVbI+Ted/txz+ymfztn2qFm3E68EbtZyPSWUnARs\nqNUoIiRTpzmqP1JScCfi4nGPkYs5ZS9SHKP4LCkCgYEA25OGm7t/fSOOX1z3Q0NJ\nBwQnaAxrhab2nAjso54KbnPSNi+huH5kHIzDHDiNjzoNi4rLVIipalfrbaSGbP0N\nkpbBDCy39qfDy/U67NFUndqvJ1KZfFDP8imo0pf+dRjiIHvwHOoFILKd0LlXpGP0\nualTO27nB2GdBleyP7w6HEkCgYEA295NxKiOumdA5kNOQXwGOj9HICmL9DzRQlCH\nrl27SOfpIUyiw/Fj8VZ08CqfJRmR3hSGThE9INSdDMvCXzvPeBJFhCYPBAeB6HIc\n4//ezbTOPC43XtxHptHNSmC31DwJR0cUhD/dWwrlDI3oDkEITYvSx9yM3NJF7o1w\nYbilqyMCgYBRR/cYRvwWksbtPji5yXqLAlqkBZT30KqRcCxJFQO/h1hVfqRa606b\n0u+Wzsh4MIE7GpHSJRSxrQIVgEXSqooPrYagvx0KTWgJZCn/6C1ukbks0ULH5hJU\nDl/UNTeYmTF73OUxjt9/Dx+kWDe9PtMkty18Xr1e2h+KbYQqW78XIQKBgFlY1TF9\nbcLCAtWPtFVYGQ/CdxzSxVTTAhZ4sypgXKMb2tj1U49coMiJ4atXJqTk5yngHVPM\nHZMh01BH3QzmOUEJ68Xv0VpJ0riq5qKgb+IX/1blUQrzaQqZZ1s6Qnm0i/CzKds0\nOLeujbW0VQC13LHmiBk/vt5ddJ2kTG7poikRAoGAVqU5Lw6x63/3aTjbEnyJXC91\nUEm3N3PU8f6mTq8nopxRH1FrfIB1vH7xgnV8HnHi6e7FkGXc7XimgaUDFPzBkQ7/\n5ig/aFwt4bllqXz1x8dXM6/fBd4QyqU51UdDccHgsSmp++8+sg2KOwBVd6DRIthA\nsC+cmgOcCELofm4I6X8=\n-----END PRIVATE KEY-----
      
      # 기본 OAuth2 클라이언트(mwm-app) 자동 등록 정보
      - IDP_MWM_CLIENT_ID=mwm-client
      - IDP_MWM_CLIENT_SECRET=mwm-secret
### 5-3. RSA 개인키 상세 가이드 (Usage & Generation)

`IDP_RSA_PRIVATE_KEY`는 OIDC의 핵심 보안 요소로, 다음과 같은 용도와 절차로 관리됩니다.

#### ① 용도 (Why is this needed?)
- **ID Token 서명**: 사용자가 로그인할 때 발행되는 **ID Token(JWT)**이 변조되지 않았음을 보장하기 위해 **RS256(RSA Signature with SHA-256)** 알고리즘으로 서명할 때 사용합니다.
- **공개키 노출**: IDP 서버는 이 개인키에서 추출한 공개키를 `/.well-known/jwks.json` 경로에 노출하며, 클라이언트(MinIO 등)는 이를 가져와 토큰의 정당성을 검증합니다.

#### ② 생성 및 포맷팅 방법 (How to Create & Format)
운영 서버의 터미널에서 아래 과정을 순서대로 실행하여 환경변수 값을 준비합니다.

```bash
# 1. 2048비트 RSA 개인키(Private Key) 생성
openssl genrsa -out idp_private.pem 2048

# 2. (선택) 개인키를 PKCS#8 포맷으로 변환 (보안 및 호환성 강화)
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in idp_private.pem -out idp_private_v2.pem

# 3. 환경변수 주입을 위해 파일 내용을 '한 줄 문자열'로 변환 (\n 포함 처리)
# 아래 명령은 모든 줄 끝에 \n 문자를 붙여 출력해 줍니다.
awk '{printf "%s\\n", $0}' idp_private_v2.pem
```

#### ③ 주입 예시
위 3번 과정에서 출력된 `-----BEGIN PRIVATE KEY-----\n...` 전체 문자열을 복사하여 아래와 같이 설정합니다.

```yaml
      # docker-compose.yml 예시
      - IDP_RSA_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIIEugIBADANBgk... (전체 내용) ...CELofm4I6X8=\n-----END PRIVATE KEY-----\n
```

---

---

## 6. Step 4: 빌드 및 기동 (Build & Run)

[Project Rules](../../.agent/project_rules.md)에 따라 확실한 재빌드 절차를 수행합니다.

```bash
# 1. 기존 컨테이너 중지 및 삭제
docker compose stop mwm-idp && docker compose rm -f mwm-idp

# 2. 이미지 빌드 (캐시 미사용)
docker compose build --no-cache mwm-idp

# 3. 컨테이너 기동
docker compose up -d mwm-idp
```

---

## 7. Step 5: 초기 사용자 동기화 (Initial Sync)

서비스 기동 시 자동으로 수행되지만, 명시적으로 `mwm-app`의 사용자(`ab_user`)를 가져오려면 API를 호출합니다.

```bash
# mwm-idp 컨테이너 내부에서 동기화 명령 실행 (또는 REST API 호출)
curl -X POST http://localhost:5000/api/sync/mwm_app
```

로그를 통해 동기화 결과를 확인합니다.
`docker compose logs -f mwm-idp`

---

## 8. Step 6: 관리자 API Key 발급 (Admin Security)

IDP 관리용 API를 안전하게 사용하기 위해 관리자 계정의 API Key를 발급합니다.

1. **로그인**: `idp.mwm.local` UI에 `Admin` 권한 계정으로 로그인합니다.
2. **콘솔 이동**: `관리자 콘솔` 메뉴 또는 `/admin/settings`로 이동합니다.
3. **Key 생성**: `관리자 전용 API Key` 섹션에서 `새 키 발급/갱신 (Rotate Key)`을 누릅니다.
4. **확인**: 발급된 `mwm_sk_...` 키를 안전하게 보관합니다.

---

## 9. 트러블슈팅 (Troubleshooting)

### 9-1. "Database connection error" 발생 시
- `SYNC_MWM_DB_URI` 환경변수의 DB 접속 정보가 정확한지, `mwm-db` 컨테이너가 정상 기동 중인지 확인합니다.

### 9-2. ID Token 서명 검증 실패 (`RS256`)
- `IDP_RSA_PRIVATE_KEY`가 올바른 PEM 포맷인지, 개행 처리가 정확하게 되어 주입되었는지 확인합니다.
- `idp/app/config.py`에서 전달된 환경변수가 정상적으로 로드되었는지 로그를 통해 확인합니다.

### 9-3. redirect_uri 불일치 에러
- IDP 어드민 콘솔에서 등록한 클라이언트의 `Redirect URI`와 실제 호출하는 주소가 스키마(http/https)까지 정확히 일치하는지 점검합니다.

---

## 10. 관련 문서
- [HOWTO 005 - SSL 인증서 생성](./HOWTO_005_generate_ssl_certificates.md)
- [HOWTO 006 - MinIO OIDC 연동 가이드](./HOWTO_006_minio_oidc_integration_guide.md)
- [SPEC 012 - OAuth2 IDP 설계서](./SPEC_012_oauth2_idp_server.md)
