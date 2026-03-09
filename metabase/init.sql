-- Metabase 전용 데이터베이스 및 권한 설정
-- 이 파일은 Metabase 전용 DB를 초기화할 때 사용합니다.

CREATE DATABASE metabase;
GRANT ALL PRIVILEGES ON DATABASE metabase TO tiffanie;
ALTER DATABASE metabase OWNER TO tiffanie;

-- Metabase가 테이블을 생성할 수 있도록 public 스키마 권한 부여 (PostgreSQL 15+)
\c metabase
GRANT ALL ON SCHEMA public TO tiffanie;
