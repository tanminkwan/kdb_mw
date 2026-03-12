# 004_SPEC_dashboard_ssl_status

## 1. 개요
Metabase 대시보드의 기능을 앱 내 `myindex` 화면으로 이식하고, 데이터 가독성 및 운영 편의성을 높이기 위한 강화 작업을 수행함.

## 2. 주요 변경 사항

### 2.1. SSL 인증서 만료 현황 블럭 추가
- **기능**: SSL 인증서의 만료 상태(만료, 임박, 주의, 정상, 미확인)를 집계하여 대시보드에 표시.
- **상세**:
    - `만료`: 만료일 <= 현재
    - `임박`: 현재 < 만료일 <= 7일 이내
    - `주의`: 7일 < 만료일 <= 30일 이내
    - `정상`: 30일 < 만료일
    - `미확인`: 만료일 정보 없음
- **이동**: 각 상태 클릭 시 `/webdomainmodelview/list/` 화면으로 이동하며, 해당 상태의 데이터만 보이도록 필터 파라미터 전달.

### 2.2. 조건부 블럭 노출 (Hide/Show)
- **대상**: [Agent 상태]를 제외한 모든 섹션 (WAS 상태, 설정 변경, 신규 지식, 오류 소식 등).
- **로직**: 각 API 호출 결과 데이터가 0건인 경우 대시보드에서 해당 카드(Card)를 숨김 처리하여 화면 공간 효율화.

### 2.3. WebDomainModelView 강화
- **추가**: `WebDomainModelView` 리스트에 `Landscape` 컬럼 추가.
- **목적**: 도메인 목록에서 해당 서버의 환경(운영/개발 등)을 즉시 확인 가능. (단, FAB 검색 제약으로 검색 필터에서는 제외)

## 3. 수정 파일 목록
- `app/sqls/monitor.py`: `get_cert_expiry_stat()` 함수 추가 (상태 집계 SQL).
- `app/views/monitor.py`: `/monitor/cert_expiry_stat` API 엔드포인트 추가.
- `app/views/was.py`: `WebDomainModelView`의 `list_columns`, `label_columns` 수정.
- `app/templates/my_index.html`: 레이아웃 변경, CSS 추가, JS 로직(AJAX 및 조건부 숨김) 적용.
- `config.py`: 앱 버전 업데이트.

## 4. 사용 방법
1. 대시보드(`myindex`) 접속 시 우측에 SSL 인증서 현황 확인 가능.
2. 특정 숫자를 클릭하면 해당 도메인 리스트로 이동.
3. 리스트 상단 검색 또는 컬럼을 통해 `Landscape` 확인 가능.
