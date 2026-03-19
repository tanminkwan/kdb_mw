# SPEC_011: Web/WAS Re-registration from Raw Text

## 1. Background (변경 배경)
- 에이전트를 통해 수집된 WebToB 설정 원본(`web_text`) 및 JEUS 설정 원본(`was_text`)은 DB에 저장되어 있으나, 파싱 로직 변경이나 데이터 유실 시 이를 다시 반영하기 위해서는 에이전트의 재수집을 기다려야 함.
- 사용자(운영자)가 원할 때 언제든지 DB에 저장된 원본 텍스트를 기반으로 하위 정보(VHost, URI, SSL, Domain, DataSource, Application 등)를 재생성할 수 있는 수동 보정 도구가 필요함.

## 2. Technical Spec (기술 사양)
### WebToB 재등록
- `MwWeb` 테이블의 `web_text` 컬럼에 저장된 `http.m` 원본 데이터를 읽어옴.
- `httpmToDict` 함수를 사용하여 텍스트를 구조화된 JSON(Dict)으로 변환.
- `newgeneration_yn` (차세대 여부)에 따라 `NewHttpm` 또는 `OldHttpm` 객체를 생성.
- `upsertWebtobHttpm()` 메서드를 호출하여 관련 모든 테이블 정보를 동기화(Upsert).
- **관계 동기화**: `upsertWebtobHttpm` 내부에서 `update_was_web_relation`을 호출하여 WAS와의 연계 정보를 즉시 갱신함.

### WAS(JEUS) 재등록
- `MwWas` 테이블의 `was_text` 컬럼에 저장된 `domain.xml` 또는 `JEUSMain.xml` 원본 데이터를 읽어옴.
- `app.sqls.agent_dml.AutorunResult.update_domain(domain_info)` 메서드를 호출.
- 내부적으로 `xmltodict`를 사용하여 파싱하고, `NewJeusDomain` 또는 `OldJeusDomain` 객체를 생성하여 정보를 동기화(Upsert).

### 설계 주의사항
- **계층 구조 준수**: View(UI) 레이어에서 DML 모듈을 직접 참조하는 대신, 서비스 레이어(예: `app/sqls/batch.py`)를 통해 중계하는 방식으로 구현하여 아키텍처 일관성을 유지함.

## 3. Modified Files (수정 파일 목록)
- `app/views/was.py`:
    - `WebModelView`에 `재등록 (Web Text 기반)` 액션 추가.
    - `WasModelView`에 `재등록 (Was Text 기반)` 액션 추가.
- `app/sqls/batch.py`:
    - `re_register_web_from_text(web_id)` 서비스 함수 구현.
    - `re_register_was_from_text(was_id)` 서비스 함수 구현.

## 4. Usage & Operation (사용 및 운영)
- WebToB 또는 WAS 목록 화면에서 하나 이상의 레코드를 선택.
- 상단 액션 메뉴에서 `재등록 (... Text 기반)` 클릭.
- 작업 완료 후 상세 정보 및 하위 목록(URI, VHost, DataSource 등)이 갱신되었는지 확인.
