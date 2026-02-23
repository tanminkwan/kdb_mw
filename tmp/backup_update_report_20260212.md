# 백업본(20260116) 업데이트 관련 이슈 및 조치사항 리포트
**일시:** 2026-02-12
**대상:** /home/hennry/projects/kdb_mw_20260116 -> 현재 프로젝트 적용

---

## 1. 데이터베이스 스키마(Schema) 관련
최신 모델 파일 분석 결과, 기존 DB에 `ALTER` 작업이 필요한 항목들이 발견되었습니다. (상세 내용은 `tmp/migration_20260212.sql` 참조)

*   **컬럼 타입 변경 (String -> Text):**
    *   `ag_command_type`, `ag_command_master`, `ag_command_detail` 테이블의 `additional_params` 컬럼.
    *   기존 1000자 제한에서 무제한(Text)으로 변경됨에 따라 `ALTER TYPE` 필요.
*   **제약 조건 완화:**
    *   `mw_server` 테이블의 `running_type` 컬럼이 필수(NOT NULL)에서 선택으로 변경됨.
*   **Enum 타입 확장:**
    *   `OSEnum`에 `LINUX-REDHAT`, `LINUX-ORACLE`, `SUNOS` 등 다수의 새로운 값이 추가됨. PostgreSQL 사용 시 `ALTER TYPE`을 통한 값 추가 필수.

## 2. 파이썬 소스 코드 문법 오류 (Syntax Errors)
백업본 소스 자체에 포함되어 있던 런타임 에러 유발 요소들을 수정하였습니다.

*   **f-string 따옴표 중첩 오류:**
    *   **발생 파일:** `app/jobs.py` (27라인), `app/sqls/batch.py` (139라인)
    *   **현상:** `f"...{rec["key"]}..."`와 같이 f-string 내부와 외부에서 모두 큰따옴표(")를 사용하여 파싱 에러 발생.
    *   **조치:** 내부 따옴표를 작은따옴표(')로 변경하여 해결.

## 3. 의존성 및 모듈 참조 문제
*   **삭제된 `auto_report` 참조:**
    *   **발생 파일:** `knowledge.py`, `monitor.py`, `git.py`, `batch.py` 등.
    *   **현상:** 사용하지 않기로 하여 삭제한 `app/auto_report` 모듈을 여전히 `import`하고 호출하고 있어 `ImportError` 발생.
    *   **조치:** 해당 모듈의 `import` 및 `send_kdbMail`, `run_auto_report` 호출부를 모두 주석 처리.

## 4. 스케줄러(Scheduler) 설정 오류
*   **중복 Job ID 사용:**
    *   **발생 파일:** `app/jobs.py`
    *   **현상:** `job_ag_finish_commands` ID가 두 개의 서로 다른 태스크(함수)에 중복 지정되어 스케줄러 등록 시 충돌 위험.
    *   **조치:** `notify_was_abnormal_status` 함수의 작업 ID를 고유하게 변경.

## 5. Flask 버전 및 스토리지 호환성 조치 (Compatibility)
*   **`send_file` 함수의 인자명 및 스토리지 불일치 해결:**
    *   **발생 파일:** `app/views/agent.py`, `app/views/was.py`
    *   **현상 1 (Syntax):** Flask 2.2+ 버전에서 `attachment_filename` 인자가 제거되어 `TypeError` 발생.
    *   **현상 2 (Storage):** 백업 소스에서 파일 업로드는 S3(MinIO)를 사용하지만, 에이전트 다운로드 뷰(`agent.py`)는 로컬 디스크(`FileManager`)를 참조하여 `FileNotFoundError` 발생.
    *   **조치:** 
        *   `attachment_filename`을 `download_name`으로 변경.
        *   `S3FileManager`와 `BytesIO`를 사용하여 MinIO 저장소의 파일을 메모리 스트리밍 방식으로 전달하도록 수정하여 로컬 디스크 의존성 제거.

*   **SQLAlchemy 서브쿼리 경고 해결:**
    *   **발생 파일:** `app/sqls/agent.py` (getLatestFile)
    *   **현상:** 암시적 서브쿼리 사용으로 인한 `SAWarning` 발생.
    *   **조치:** `.scalar_subquery()`를 명시적으로 사용하여 최신 SQLAlchemy 버전과의 호환성 확보.

## 6. MwWasHttpListener 모델 및 로직 업데이트 (2026-02-19)
*   **모델 및 뷰 필드 추가:**
    *   `MwWasHttpListener` 모델에 `ssl_yn` (Enum), `domain_name` (String) 컬럼을 추가하였습니다.
    *   `WasHttpListenerModelView`의 목록 및 상세 화면에 해당 필드를 노출하고 레이블을 지정하였습니다.
*   **데이터 자동 수집 및 설정 로직:**
    *   `app/dmlsForJeus.py`를 수정하여 JEUS 구성 정보 업서트 시 리스너의 `ssl` 설정 유무를 확인합니다.
    *   지정된 리스너에 `ssl` 설정이 존재하면 `ssl_yn` 값을 `'YES'`로, 그렇지 않으면 `'NO'`로 자동 저장하도록 로직을 구현하였습니다.
*   **필수 DB 스키마 변경 (Migration SQL):**
    ```sql
    -- mw_was 테이블 누락 컬럼 추가
    ALTER TABLE mw_was ADD COLUMN blackout_info TEXT;

    -- mw_was_httplistener 테이블 신규 컬럼 추가
    ALTER TABLE mw_was_httplistener ADD COLUMN ssl_yn VARCHAR(10);
    ALTER TABLE mw_was_httplistener ADD COLUMN domain_name VARCHAR(200);

    -- mw_web 테이블 tmp_text1~8 컬럼 추가
    ALTER TABLE mw_web ADD COLUMN tmp_text1 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text2 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text3 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text4 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text5 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text6 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text7 VARCHAR(500);
    ALTER TABLE mw_web ADD COLUMN tmp_text8 VARCHAR(500);
    ```
*   **외래 키 제약 조건 위반 조치:**
    *   `mw_was` 또는 `mw_web` 테이블에 데이터를 인설트할 때 `located_host_id` 또는 `host_id`가 `mw_server` 테이블에 존재해야 합니다.
    *   `prdwaa11` 서버 정보가 없는 경우 아래와 같이 `mw_server`에 기본 정보를 먼저 등록해야 합니다.
    ```sql
    INSERT INTO mw_server (host_id, ip_address, os_type, landscape, use_yn, user_id, create_on)
    VALUES ('prdwaa11', '127.0.0.1', 'LINUX', 'PRD', 'YES', 'tiffanie', NOW());
    ```

## 7. DB 데이터 확인 방법 (Docker)
에이전트로부터 수집된 데이터가 올바르게 DB에 반영되었는지 확인하려면 아래 Docker 명령어를 사용합니다.

*   **HTTP 리스너 수집 결과 확인:**
    ```bash
    docker exec mwm-db psql -U postgres -d mw -c "SELECT was_id, was_instance_id, webconnection_id, listen_port, ssl_yn, domain_name FROM mw_was_httplistener WHERE was_id = 'PRDW_Domain';"
    ```

## 8. WebTob 및 WAS 구성도(Relationship Diagram) 로직 개선 (2026-02-23)
구성도 시각화의 정확성과 가독성을 높이기 위해 매핑 로직 및 정렬 방식을 개선하였습니다.

*   **URI_JSV 연결 정확도 향상:**
    *   `SVRNAME` 컬럼에 콤마(`,`)로 구분된 다수 서버명이 포함된 경우를 정상적으로 지원하도록 파싱 로직을 보강했습니다.
    *   `SVGNAME`을 기반으로 `SERVER` 섹션에서 대상 서버를 우선적으로 찾도록 개선하고, 매칭되는 서버가 없을 경우 `SVRGROUP`의 `LBSERVERS` 정보를 참조하는 Fallback 로직을 추가했습니다.
*   **시각적 정렬 및 연결선 꼬임 방지:**
    *   구성도의 오퍼레이터 포트(Connector) 이름이 알파벳 순으로 자동 정렬되면서 순서가 어긋나는 문제를 해결했습니다.
    *   `RPROXY`, `URI`, `WAS`, `WEB` 등 모든 주요 오퍼레이터의 포트 ID 앞에 3자리 순번 접두어(예: `001_`, `002_`)를 부여하여 리스트의 원래 순서대로 포트가 배치되도록 고정했습니다.
    *   WAS 구성도에서 WEB 도메인의 Input/Output 포트 간 인덱스를 일치시켜 연결선이 직선으로 깔끔하게 표현되도록 개선했습니다.

## 9. JEUS 설정 동기화 및 인스턴스 자동 삭제 (2026-02-23)
JEUS 설정 XML 파일을 기반으로 데이터를 업데이트할 때, 설정에서 제거된 인스턴스가 DB에 그대로 남는 현상을 해결했습니다.

*   **인스턴스 자동 삭제 기능 추가 (`dmlsForJeus.py`):**
    *   `upsertJeusDomain` 함수 내부에서 현재 설정 파일에 포함된 인스턴스 ID 목록을 추출합니다.
    *   기존 DB 데이터 중 이번 설정에 포함되지 않은 인스턴스를 찾아 `delete` 쿼리를 수행합니다.
*   **Cascade 효과를 통한 하위 데이터 정리:**
    *   모델단의 `ondelete='CASCADE'` 설정을 활용하여, 인스턴스 삭제 시 관련 `MwWasHttpListener`, `MwWasWebtobConnector`, 매핑 정보 등이 자동으로 함께 삭제되어 데이터 무결성을 유지합니다.

## 10. API 레이어 분리 및 대시보드 디자인 고도화 (2026-02-23)
코드의 유지보수성과 확장성을 높이기 위해 View와 API 로직을 분리하고, 메인 대시보드의 UX를 개선했습니다.

*   **API 컨트롤러 이동 및 리팩토링:**
    *   `MWConfiguration`, `MwDiff` (was.py) -> `app/api/was_api.py`로 이동.
    *   `CommandApi`, `AgentApi` (agent.py) -> `app/api/agent_api.py`로 이동.
    *   각 API 컨트롤러는 전용 모듈에서 관리되며, `app/__init__.py`를 통해 통합 등록됩니다.
    *   View 파일(`was.py`, `agent.py`)에서 불필요한 import 및 API 클래스를 제거하여 관리 효율성을 높였습니다.
*   **메인 대시보드 (my_index.html) 디자인 개편:**
    *   오프라인 환경에서도 작동 가능한 Pure CSS 기반의 카드 레이아웃 대시보드를 도입했습니다.
    *   반응형 그리드 및 현대적인 컬러 팔레트를 적용하여 시인성을 극대화했습니다.
    *   기존 AJAX 기능 및 상태 모니터링 로직과 호환성을 유지하면서 최신 트렌드를 반영한 UI로 개선했습니다.

---
**비고:** 모든 파이썬 파일에 대해 `py_compile` 검사를 완료하였으며, 비즈니스 로직상의 정렬 및 데이터 무결성 보완 작업이 완료되었습니다. (현재 앱 버전: `20260223.005`)

