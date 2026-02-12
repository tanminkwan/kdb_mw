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

---
**비고:** 모든 파이썬 파일에 대해 `py_compile` 검사를 완료하였으며, 현재 문법적인 문제는 없는 상태입니다.
