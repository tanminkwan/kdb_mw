# Metabase 대시보드 관리 및 프로비저닝 가이드 (As Code)

본 문서는 Metabase 대시보드를 코드로 관리(`Configuration as Code`)하고, 이를 활용하여 마이그레이션하거나 기능을 확장하는 방법을 상세히 설명합니다.

---

## 1. 개요
Metabase는 선택적(Optional) 구성 요소입니다. 운영의 일관성과 마이그레이션 편의성을 위해 **API 기반 자동 설정 스크립트**를 제공합니다. DB 전체를 백업/복구할 필요 없이 명세 파일(`provisioning.json`)만 관리하면 어디서든 동일한 대시보드를 재현할 수 있습니다.

### 핵심 구성 파일
- **`metabase/init.sql`**: Metabase 전용 데이터베이스(`metabase`) 및 권한 생성 스크립트
- **`metabase/provisioning.json`**: 대시보드 구조 및 SQL 쿼리 명세 (데이터)
- **`metabase/setup.py`**: API를 사용하여 Metabase를 초기화하고 명세를 반영하는 엔진 (로직)
- **`metabase/verify_setup.py`**: 명세서와 실제 메타베이스 상태를 비교 검증하는 도구
- **`metabase/health_check.py`**: 메타베이스 서비스 및 DB 연결 상태를 점검하는 독립 헬스체커
- **`metabase/README.md`**: 최신 메타베이스 API 대응 기술(`Negative ID` 등)이 포함된 운영 가이드

---

## 2. 수동 설치 및 초기 구축 방법
Metabase 설치가 필요한 경우에만 다음 순서에 따라 수동으로 구성합니다.

### 2.1 데이터베이스 초기 설정
Metabase가 자신의 설정값을 저장할 전용 데이터베이스를 생성합니다.
```bash
# mwm-db 컨테이너 내부에 metabase DB 및 권한 생성
docker exec -i mwm-db psql -U postgres -f /dev/stdin < metabase/init.sql
```

### 2.2 메타베이스 서비스 시작
`docker-compose.yml`에는 이미 설정이 포함되어 있으므로 해당 서비스만 활성화합니다.
```bash
docker compose up -d mwm-metabase
```

### 2.3 프로비저닝 실행 (대시보드 자동 구축)
Metabase 서버가 완전히 기동된 후(약 1~2분 소요), 관리자 계정과 대시보드를 자동으로 생성합니다.

#### 방법 A: 로컬에서 직접 실행 (권장)
작업 PC에 Python이 설치되어 있는 경우 가장 빠르고 확실한 방법입니다.  
**※ 주의**: `docker-compose.yml`에서 `mwm-db`의 포트(`5433:5432`)가 열려 있어야 합니다.

```bash
# 1. 필요한 라이브러리 설치
pip install requests

# 2. 환경 변수 설정 및 실행 (한 번에 복사)
export METABASE_URL=http://localhost:3000
export DB_HOST=localhost
export DB_PORT=5433
export DB_NAME=mw
export DB_USER=tiffanie
export DB_PASS='1q2w3e4r!!'
export METABASE_ADMIN_EMAIL=admin@example.com
export METABASE_ADMIN_PASSWORD=Password123!
export METABASE_SITE_NAME='MWM Analytics'

python metabase/setup.py

#### 2.4 설정 검증 (선택 사항이나 권장)
설정이 명세서(`provisioning.json`)와 완벽하게 일치하는지 검증합니다. 모든 항목이 **✅ PASS**로 나와야 성공입니다.
```bash
python metabase/verify_setup.py
```
```

#### 방법 B: Docker를 이용한 실행 (옵션)
호스트에 Python 환경이 없을 때 사용합니다.
```bash
docker run --rm --network mw_app_default \
  -v $(pwd)/metabase:/metabase \
  -e METABASE_URL=http://mwm-metabase:3000 \
  -e DB_HOST=mwm-db \
  -e DB_NAME=mw \
  -e DB_USER=tiffanie \
  -e DB_PASS='1q2w3e4r!!' \
  python:3.9-slim sh -c "pip install requests && python /metabase/setup.py"
```

---

## 3. 환경 변수 상세 가이드
스크립트 실행 시 사용되는 모든 환경 변수의 의미입니다.

| 변수명 | 설명 | 기본값(소스코드 내) | 로컬 실행 시 권장값 |
| :--- | :--- | :--- | :--- |
| `METABASE_URL` | Metabase 서버 접속 주소 | `http://mwm-metabase:3000` | `http://localhost:3000` |
| `DB_HOST` | 에이전트 데이터(`mw`) DB 주소 | `mwm-db` | `localhost` |
| `DB_PORT` | DB 접속 포트 | `5432` | `5433` |
| `DB_NAME` | 조회할 DB 이름 | `mw` | `mw` |
| `DB_USER` | DB 사용자 계정 | `tiffanie` | `tiffanie` |
| `DB_PASS` | DB 비밀번호 | `1q2w3e4r!!` | `1q2w3e4r!!` |
| `METABASE_ADMIN_EMAIL` | 생성/로그인 할 관리자 ID | `admin@example.com` | (자유 입력) |
| `METABASE_ADMIN_PASSWORD` | 생성/로그인 할 관리자 PW | `Password123!` | (자유 입력) |
| `METABASE_SITE_NAME` | Metabase 사이트 이름 | `MWM Analytics` | `MWM Analytics` |

---

## 4. 기능 추가 및 변경 방법 (운영 및 확장)

### 4.1 새로운 질문(Card) 추가
1. **`metabase/provisioning.json`**의 `questions` 배열에 항목을 추가합니다.
2. `dashboard.cards` 배열에 배치 정보(row, col, size)를 입력합니다.
3. 위의 **프로비저닝 실행** 명령어를 다시 수행하면 새 항목만 추가됩니다.

### 4.2 기존 SQL 로직 수정
1. **`provisioning.json`** 내의 `query` 내용을 수정합니다.
2. 프로비저닝 스크립트를 재실행하면 스크립트가 기존 쿼리와 비교하여 **변경된 부분만 API를 통해 업데이트**합니다.

---

## 5. 문제 해결 (Troubleshooting)

### Q: "permission denied for schema public" 에러 발생 시
PostgreSQL 15 보안 정책 때문입니다. `metabase/init.sql`을 다시 실행하거나 아래 명령을 수행하세요.
```bash
docker exec -it mwm-db psql -U postgres -d metabase -c "GRANT ALL ON SCHEMA public TO tiffanie;"
```

### Q: "Authentication failed" 또는 접속 불가 에러
Metabase가 초기 기동 중에 내부 DB 설정을 진행하느라 응답이 늦는 경우입니다. 1분 정도 후에 다시 시도하세요.

### Q: 메타베이스 버전 업데이트 후 필터 매핑 오류 (500 Error)
Metabase v0.47 이상에서는 대시보드 카드 추가 방식이 변경되었습니다. `setup.py`는 최신 방식(Bulk Update 및 Negative ID 기술)을 지원하므로, 최신 버전의 `setup.py`를 사용하고 있는지 확인하십시오.

### Q: 시스템 상태 확인 방법
설정값과 상관없이 메타베이스 서비스 자체가 정상인지 확인하려면 다음을 실행하세요.
```bash
python metabase/health_check.py
```
