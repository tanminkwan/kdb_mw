# Project Rules

## 1. Baseline Reference
- **Baseline Path**: `/home/hennry/projects/kdb_mw_20260116/`
- **Rule**: When analyzing current code or implementing new features/refactoring, always compare the current changes with the code in the baseline path to ensure alignment and understand the evolution.

## 2. Project Execution Policy
- **Workflow**: 
  1. Modify code.
  2. **Versioning**: MUST update `APP_NAME` in `config.py`.
  3. **Apply Changes (Surefire Rebuild Policy)**:
     To guarantee code and config changes (especially `config.py`) are reflected in Docker, you **MUST** follow these 3 steps:
     - Step 1: `docker compose stop <service> && docker compose rm -f <service>`
     - Step 2: `docker compose build --no-cache <service>`
     - Step 3: `docker compose up -d <service>`
- **Constraint**: **Do NOT** assume `docker compose up --build` or just `build --no-cache` will reliably replace the container image. Always stop and remove the container before rebuilding.

## 3. Versioning Policy
- **Before Building**: Always update the `APP_NAME` in `config.py` with the current date and sequence number.
- **Format**: `리발소(VER:YYYYMMDD.seq)` (e.g., `리발소(VER:20260312.001)`)
- **Rule**: This update MUST be done before any `docker compose build` or `up --build` command.
- **Constraint**: **Do NOT** execute python scripts directly (e.g., `python run.py`) for running the application after modification. Always use the Docker-based workflow to ensure the environment is consistent and all dependencies (DB, Redis, Minio, etc.) are correctly linked.

## 4. Documentation Policy
- **Location**: `docs/` 디렉토리
- **Naming Format**: 
  - 기능 명세: `SPEC_{SEQ}_{기능명}.md` (e.g., `SPEC_001_broadcast_callback.md`)
  - 운영 가이드: `HOWTO_{SEQ}_{작업명}.md` (e.g., `HOWTO_001_create_docker_image.md`)
- **SEQ**: 3자리 순번. 각 카테고리별로 별도의 순번을 유지하거나 전체 문서의 흐름에 따라 증가시킴.
- **Content**: 변경 배경, DB Migration SQL, 수정 파일 목록, 기술 spec, 사용법, 또는 운영 절차 등을 포함.
- **Rule**: 기능 추가/변경 또는 중요한 운영 절차 수립 시 반드시 해당 문서를 작성해야 함.

## 5. Communication Policy
- **Rule**: 작업 시작 전에는 반드시 수행할 작업 내용에 대해 간략하게 설명(Plan)을 하고 진행한다.
- **Constraint**: 사용자에게 작업의 흐름을 미리 알림으로써 의도하지 않은 수정을 방지한다.

## 6. DB Query
- **Rule**: PostgreSQL(mwm-db) 조회가 필요한 경우, 다음과 같이 docker exec 명령을 사용한다.
- **Command**: `docker exec -it mwm-db psql -U tiffanie -d mw` (기본 암호는 config.py 참조)
