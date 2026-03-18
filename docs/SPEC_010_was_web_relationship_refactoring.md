# SPEC_010: WAS-WEB Relationship Refactoring (Association Table)

## 1. Background (변경 배경)
- 현재 `mw_web` 테이블은 `dependent_was_id`라는 문자열 컬럼을 사용하여 제우스 내장 WebToB와 WAS 간의 관계를 관리하고 있음.
- **문제점**:
  - 데이터 무결성 보장이 어려움 (WAS 삭제 시 관계 유지 등).
  - 등록 시점의 순서에 따라 관계 형성이 복잡해짐 (문자열 정규화 로직 의존).
  - 프로젝트 내 다른 관계(Tag, Application 등)와 일관성이 없음.
- **해결책**:
  - `dependent_was_id` 컬럼을 제거하고, `mw_was_web`이라는 **Association Table**을 도입하여 M:N 관계(실제로는 1:N 이 많음)를 지원함.
  - 문자열 ID 매칭 대신, **실제 물리적 설정값(JSV Port 또는 Web Home 경로)**을 기반으로 관계를 식별함.

## 2. Migration & Sync Strategy (이관 및 동기화 전략)
- **기존 방식 폐기**: `dependent_was_id` 문자열 기반의 SQL Migration을 수행하지 않음.
- **서버 내부 기능 (`sync_was_web_relationship`) 도입**:
    - 모든 `MwWeb` (BuiltType='Internal') 레코드를 루프 돌며, 동일 서버(`host_id`) 내의 `MwWasInstance` 및 그에 연결된 `MwWasWebtobConnector` 정보를 조회함.
    - `jsv_port` 또는 `web_home` 설정이 일치하는 경우 `assoc_was_web` 테이블에 관계 정보를 일괄 생성/갱신함.
- **실행 방식**: UI의 `Command Master` (서버내부기능)를 통해 호출 가능하도록 구현함.
- **최종 정리**: 동기화 완료 및 검증 후 `mw_web.dependent_was_id` 컬럼을 삭제함.

## 3. Modified Files (수정 파일 목록)
- `app/models/was.py`: 
    - `assoc_was_web` 테이블 정의 추가.
    - `MwWeb.dependent_was_id` 컬럼 제거.
    - `MwWas`와 `MwWeb` 클래스 간 `relationship` (secondary=assoc_was_web) 추가.
- `app/dmlsForWebtob.py`:
    - WEB 등록(`upsertWebtobHttpm`) 시, 자신의 `jsv_port`나 `web_home`을 기반으로 부모 WAS를 찾아 `mw_was_web`에 연결하는 로직 추가.
    - `httpm_object` JSON 내부에 `_dependent_was_id` 힌트 기록 (지연 연결용).
- `app/dmlsForJeus.py`:
    - WAS 등록(`upsertJeusDomain`) 시, 신규 등록된 WAS의 커넥터(JSV Port 등)와 매칭되는 미연결 WEB들을 찾아 관계를 형성하는 로직 추가.
- `app/sqls/relationship.py`:
    - `get_web_servers` 함수에서 `dependent_was_id` 대신 Association Table을 통한 조인 로직으로 변경.

## 4. Technical Spec (기술 사양)
### 내장 WEB 식별 및 매칭 로직 (Multi-Node / HA 대응)
1. **내장형 판단**: `http.m` 파일 경로에 `webserver/config` 포함 여부.
2. **매칭 기준 (Match Criteria)**:
   - **기본 원칙**: 동일 서버(`host_id`) 내에서 동작하는 **WAS Instance(MS)**의 설정을 매칭 고리로 사용.
   - **TCP 통신 시**: `MwWeb.host_id` == `MwWasInstance.host_id` AND `MwWeb.jsv_port` == `MwWasWebtobConnector.jsv_port`.
   - **Domain Socket 시**: `MwWeb.host_id` == `MwWasInstance.host_id` AND `MwWeb.web_home` == `MwWasWebtobConnector.web_home`.
   - **이점**: WAS 도메인이 여러 대의 서버에 걸쳐 있더라도, 각 서버에 설치된 내장 WEB이 해당 서버에서 도는 MS 인스턴스를 통해 정확한 부모 `MwWas` 도메인을 찾아갈 수 있음.
3. **지연된 연결 (Delayed Linking)**:
   - 부모 WAS(또는 해당 노드의 MS)가 없는 상태로 WEB이 먼저 등록되면 `Internal` 타입으로만 저장.
   - 추후 WAS가 등록될 때, 해당 WAS의 인스턴스(MS) 및 커넥터 설정을 사용하는 WEB을 역으로 추적하여 Association Table에 데이터 삽입.
4. **구성도 쿼리 최적화**:
   - `get_web_servers` 시 `MwWeb.mw_was` 관계를 조인하여 명시적인 PK 매칭 기반으로 데이터 추출.
5. **코드 재사용 원칙 (Implementation Principle)**:
   - 특정 WEB/WAS 등록 시 수행되는 관계 형성 로직과 `Command Master`에서 실행되는 일괄 동기화 로직은 핵심 매칭 로직을 공유해야 함.
   - 가급적 별도의 공통 함수(예: `update_was_web_relation(web_id=None, was_id=None)`)로 분리하여 코드 중복을 최소화하고 유지보수성을 높임.

## 5. Potential Impacts (기타 영향 파악)

### 1) UI/View 영향 (`app/views/was.py`)
- `WebCommonView`의 `list_columns` 및 `label_columns`에서 `dependent_was_id` 참조를 제거하고, 관계형 필드(예: `mw_was`)로 대체해야 함.
- 대체하지 않을 경우 WEB 목록 화면 조회 시 컬럼 부재로 인한 Runtime Error 발생 가능.

### 2) ITAM 데이터 비교 로직 (`app/sqls/itam_compare.py`)
- **가장 큰 영향**: ITAM 데이터와 로컬 데이터를 비교할 때 `dependent_was_id`를 Key로 사용하고 있음.
- 해당 파일 내의 모든 `MwWeb.dependent_was_id` 참조를 새로운 관계형 조인 또는 `httpm_object` 내의 힌트 정보 사용으로 로직 전면 수정 필요.

### 3) 엑셀 다운로드 기능
- `WebModelView`의 `Excel Download` 액션 등에서 `select *`를 사용하는 경우 컬럼 구조 변화가 결과물에 반영됨.

### 4) 데이터 마이그레이션 리스크
- 컬럼 삭제 전 반드시 `mw_was_web` 테이블로의 데이터 이관이 선행되어야 함. (Migration SQL 시퀀스 준수 필수)

## 6. Usage & Operation (사용 및 운영)
- **관계 동기화**: `Command Master` (서버내부기능)에서 `sync_was_web_relationship` 기능을 실행함.
- **검증**: `MwWas` 상세 정보 또는 구성도에서 관계가 정상인지 확인함.
- **후처리**: 모든 검증이 완료된 후, DB에서 `dependent_was_id` 컬럼을 수동 삭제(Drop)함 (또는 코드를 최종 수정하여 배포함).
