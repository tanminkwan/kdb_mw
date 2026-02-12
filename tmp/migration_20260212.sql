-- Migration SQL for KDB MW App Update (2026-02-12)

-- 1. additional_params 컬러 타입 변경 (String -> Text)
ALTER TABLE ag_command_type ALTER COLUMN additional_params TYPE TEXT;
ALTER TABLE ag_command_master ALTER COLUMN additional_params TYPE TEXT;
ALTER TABLE ag_command_detail ALTER COLUMN additional_params TYPE TEXT;

-- 2. mw_server 테이블의 running_type 제약 조건 변경 (NOT NULL 제거)
ALTER TABLE mw_server ALTER COLUMN running_type DROP NOT NULL;

-- 3. OSEnum 타입에 새로운 운영체제 값 추가
-- PostgreSQL에서 ENUM 타입인 경우 아래 명령어를 실행합니다.
-- (실제 TYPE 명칭이 'osenum'이 아닐 경우 확인이 필요할 수 있습니다.)
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-REDHAT';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-ORACLE';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-ROCKY';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-CENTOS';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-SOMANSAOS';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-OPENSUSE';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-DEBIAN';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'LINUX-UBUNTU';
ALTER TYPE osenum ADD VALUE IF NOT EXISTS 'SUNOS';
