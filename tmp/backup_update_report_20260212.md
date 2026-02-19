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

---
**비고:** 모든 파이썬 파일에 대해 `py_compile` 검사를 완료하였으며, 현재 문법 및 주요 런타임 라이브러리 호환성 문제는 해결된 상태입니다.

