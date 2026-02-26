# ITAM 대사 실행 Flow

> **관련 파일**  
> - View: `app/views/itam.py`  
> - SQL: `app/sqls/itam_compare.py`  
> - API: `app/api/itam_compare_api.py`  
> - Model: `app/models/itam.py`  
> - Template: `app/templates/itam_compare.html`

---

## 1. 일괄 대사 실행

### 호출 흐름

```
[브라우저] "일괄 대사 실행" 버튼 클릭
  │
  │  POST /api/v1/itam-compare/run-all
  ▼
[API] itam_compare_api.py
  │  Class: ItamCompareApi
  │  Method: run_all()
  ▼
[SQL] itam_compare.py
  │  Function: run_all_compare()
  │
  │  ① 기존 대사 결과 4개 테이블 전체 DELETE
  │     - it_itam_was_compare
  │     - it_itam_web_compare
  │     - it_leebalso_was_compare
  │     - it_leebalso_web_compare
  │
  │  ② 6가지 대사 함수 순차 실행 (아래 상세)
  │  ③ 결과 INSERT → db.session.commit()
  │  ④ summary dict 반환
  ▼
[API] JSON 응답 → { summary: { itam_was: N건, ..., total: N건 } }
  │
  ▼
[브라우저] 결과 summary 표시 + 4개 탭 자동 새로고침
  │  GET /api/v1/itam-compare/results/itam-was
  │  GET /api/v1/itam-compare/results/itam-web
  │  GET /api/v1/itam-compare/results/leebalso-was
  │  GET /api/v1/itam-compare/results/leebalso-web
  ▼
  완료
```

---

## 2. 6가지 대사 함수 상세

### 2-1. ITAM WAS 기준 대사

| 항목 | 내용 |
|------|------|
| **SQL 함수** | `itam_compare.py` → `compare_itam_was(config_id=None)` |
| **내부 호출** | `_get_itam_was_filtered()`, `_get_valid_host_ids()`, `_is_agent_inactive()` |
| **원본 테이블** | `it_was` |
| **비교 테이블** | `mw_was`, `mw_server`, `mw_was_httplistener`, `ag_agent` |
| **결과 테이블** | `it_itam_was_compare` (Model: `ItItamWasCompare`) |

**필터 조건**:
- `config_status != '불용'`
- `run_env in ('운영', '이관', '개발')`
- `config_name not like '%(S)%'`
- `install_user not like 'tmax%'`
- *(run_env, domain_name)으로 그룹핑, host_id 알파벳순 첫번째가 대표*

**오류 체크 (6가지)**:

| # | 오류 항목 | 비교 로직 |
|---|----------|----------|
| 1 | `hostname 미등록` | `host_id`가 `mw_server(use_yn='YES')`에 없음 |
| 2 | `WAS 미등록` | `(domain_name, run_env→LocationEnum)` 조합이 `mw_was(was_id, landscape)`에 없음 |
| 3 | `설치 서버 불일치` | `host_id != mw_was.located_host_id` |
| 4 | `WAS SSL 불일치` | `mw_was_httplistener`에 `ssl_yn='YES'` 존재 여부와 `was_ssl_yn` 불일치 |
| 5 | `Agent 없음` | `mw_was.agent_id`가 null 또는 빈 문자열 |
| 6 | `Agent 비활성화` | `ag_agent.last_checked_date`가 현재보다 5분 이상 경과 |

---

### 2-2. ITAM 내장WEB 기준 대사

| 항목 | 내용 |
|------|------|
| **SQL 함수** | `itam_compare.py` → `compare_itam_embed_web(config_id=None)` |
| **원본 테이블** | `it_was` (embed_web_yn = 'Y') |
| **비교 테이블** | `mw_web` |
| **결과 테이블** | `it_itam_was_compare` (Model: `ItItamWasCompare`) — *WAS와 같은 테이블* |

**필터 조건**:
- `config_status != '불용'`
- `run_env in ('운영', '이관', '개발')`
- `config_name not like '%(S)%'`
- `embed_web_yn = 'Y'`

**오류 체크 (5가지)**:

| # | 오류 항목 | 비교 로직 |
|---|----------|----------|
| 1 | `내장 WEB 미등록` | `(host_id, embed_web_port)`가 `mw_web(host_id, port)`에 없음 |
| 2 | `내장 WEB SSL 여부 불일치` | `embed_web_ssl_yn` ↔ `mw_web.t__ssl_yn()` 불일치 |
| 3 | `운용환경 불일치` | `run_env→LocationEnum` ↔ `mw_web.landscape` 불일치 |
| 4 | `내장 웹 구분 이상` | `mw_web.built_type != BuiltEnum.Internal` |
| 5 | `WAS Domain 이상` | `domain_name != mw_web.dependent_was_id` |

---

### 2-3. ITAM WEB 기준 대사

| 항목 | 내용 |
|------|------|
| **SQL 함수** | `itam_compare.py` → `compare_itam_web(config_id=None)` |
| **내부 호출** | `_get_valid_host_ids()`, `_is_agent_inactive()` |
| **원본 테이블** | `it_web` |
| **비교 테이블** | `mw_web`, `mw_server`, `ag_agent` |
| **결과 테이블** | `it_itam_web_compare` (Model: `ItItamWebCompare`) |

**필터 조건**:
- `config_status != '불용'`
- `run_env in ('운영', '이관', '개발')`
- `config_name not like '%(S)%'`

**오류 체크 (6가지)**:

| # | 오류 항목 | 비교 로직 |
|---|----------|----------|
| 1 | `hostname 미등록` | `host_id`가 `mw_server(use_yn='YES')`에 없음 |
| 2 | `WEB 미등록` | `(host_id, node_port)`가 `mw_web(host_id, port)`에 없음 |
| 3 | `WEB SSL 여부 불일치` | `ssl_yn` ↔ `mw_web.t__ssl_yn()` 불일치 |
| 4 | `운용환경 불일치` | `run_env→LocationEnum` ↔ `mw_web.landscape` 불일치 |
| 5 | `Agent 없음` | `mw_web.agent_id`가 null 또는 빈 문자열 |
| 6 | `Agent 비활성화` | `ag_agent.last_checked_date`가 현재보다 5분 이상 경과 |

---

### 2-4. 리발소 WAS 기준 대사

| 항목 | 내용 |
|------|------|
| **SQL 함수** | `itam_compare.py` → `compare_leebalso_was(was_id=None)` |
| **원본 테이블** | `mw_was` |
| **비교 테이블** | `it_was` |
| **결과 테이블** | `it_leebalso_was_compare` (Model: `ItLeebalsoWasCompare`) |

**필터 조건**: `use_yn = 'YES'`

**오류 체크 (1가지)**:

| # | 오류 항목 | 비교 로직 |
|---|----------|----------|
| 1 | `ITAM 미등록` | `(was_id, landscape→run_env)`가 `it_was(domain_name, run_env)`에 없음 |

---

### 2-5. 리발소 내장WEB 기준 대사

| 항목 | 내용 |
|------|------|
| **SQL 함수** | `itam_compare.py` → `compare_leebalso_embed_web(web_id=None)` |
| **원본 테이블** | `mw_web` |
| **비교 테이블** | `it_was` |
| **결과 테이블** | `it_leebalso_web_compare` (Model: `ItLeebalsoWebCompare`) |

**필터 조건**: `use_yn = 'YES'`, `built_type = '내장'`

**오류 체크 (1가지)**:

| # | 오류 항목 | 비교 로직 |
|---|----------|----------|
| 1 | `ITAM 미등록` | `(host_id, port)`가 `it_was(host_id, embed_web_port, embed_web_yn='Y')`에 없음 |

---

### 2-6. 리발소 WEB(외장) 기준 대사

| 항목 | 내용 |
|------|------|
| **SQL 함수** | `itam_compare.py` → `compare_leebalso_web(web_id=None)` |
| **원본 테이블** | `mw_web` |
| **비교 테이블** | `it_web` |
| **결과 테이블** | `it_leebalso_web_compare` (Model: `ItLeebalsoWebCompare`) |

**필터 조건**: `use_yn = 'YES'`, `built_type != '내장'`

**오류 체크 (1가지)**:

| # | 오류 항목 | 비교 로직 |
|---|----------|----------|
| 1 | `ITAM 미등록` | `(host_id, port)`가 `it_web(host_id, node_port)`에 없음 |

---

## 3. 단건 대사 실행

| API 엔드포인트 | SQL 함수 | 설명 |
|---------------|---------|------|
| `POST /api/v1/itam-compare/itam-was/<config_id>` | `compare_single_itam_was(config_id)` | 해당 config_id의 WAS + 내장WEB 대사 |
| `POST /api/v1/itam-compare/itam-web/<config_id>` | `compare_single_itam_web(config_id)` | 해당 config_id의 WEB 대사 |
| `POST /api/v1/itam-compare/leebalso-was/<id>` | `compare_single_leebalso_was(was_id)` | 해당 mw_was.id의 ITAM 미등록 대사 |
| `POST /api/v1/itam-compare/leebalso-web/<id>` | `compare_single_leebalso_web(web_id)` | 내장/외장 판별 후 해당 mw_web.id 대사 |

---

## 4. View & 메뉴 구성

| View 클래스 | 파일 | 메뉴명 | 카테고리 |
|------------|------|--------|---------|
| `ItamCompareView` | `views/itam.py` | 대사 실행 | ITAM 대사 |
| `ItItamWasCompareModelView` | `views/itam.py` | ITAM WAS 기준 대사 | ITAM 대사 |
| `ItItamWebCompareModelView` | `views/itam.py` | ITAM WEB 기준 대사 | ITAM 대사 |
| `ItLeebalsoWasCompareModelView` | `views/itam.py` | 리발소 WAS 기준 대사 | ITAM 대사 |
| `ItLeebalsoWebCompareModelView` | `views/itam.py` | 리발소 WEB 기준 대사 | ITAM 대사 |

---

## 5. 데이터 변환 함수

| 함수 | 파일 | 용도 |
|------|------|------|
| `run_env_to_location(run_env)` | `sqls/itam_compare.py` | ITAM `run_env`(운영/이관/개발) → `LocationEnum`(PROD/TEST/DEV) |
| `location_to_run_env(location_name)` | `sqls/itam_compare.py` | `LocationEnum` → ITAM `run_env` (역변환) |
| `_ssl_yn_matches(itam_ssl, leebalso_ssl)` | `sqls/itam_compare.py` | ITAM `ssl_yn`('Y'/'N') ↔ 리발소 `ssl_yn`('YES'/'NO') 비교 |
| `_is_agent_inactive(agent_id)` | `sqls/itam_compare.py` | Agent 비활성화 여부 (5분 기준) |
| `_get_valid_host_ids()` | `sqls/itam_compare.py` | `mw_server(use_yn='YES')`의 host_id 집합 조회 |
| `_get_itam_was_filtered()` | `sqls/itam_compare.py` | ITAM WAS 필터링 + (run_env, domain_name) 그룹핑 |

---

## 6. 데이터 흐름 요약

```
ITAM 기준 대사 (ITAM에 있는데 리발소에 이상 있는 것 찾기)

  it_was  ──비교──→  mw_was, mw_server, mw_was_httplistener, ag_agent
  it_was  ──비교──→  mw_web (내장WEB)
  it_web  ──비교──→  mw_web, mw_server, ag_agent

리발소 기준 대사 (리발소에 있는데 ITAM에 없는 것 찾기)

  mw_was  ──비교──→  it_was
  mw_web  ──비교──→  it_was (내장) 또는 it_web (외장)
```
