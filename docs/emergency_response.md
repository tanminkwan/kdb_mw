# 비상대응 가이드

> **환경**: Docker Compose (`mwm-app`, `mwm-db`, `mwm-redis`, `mwm-minio`, `mwm-kroki`, `mwm-kroki-mermaid`)

---

## 1. DB 세션 강제 종료

DB 락, 세션 꼬임, `RuntimeError: number of values in row` 등 DB 관련 오류 발생 시.

```bash
# mw 데이터베이스의 모든 세션 강제 종료 (현재 세션 제외)
docker exec mwm-db psql -U postgres -d mw -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'mw' AND pid != pg_backend_pid();
"
```

### 현재 활성 세션 확인
```bash
docker exec mwm-db psql -U postgres -d mw -c "
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity 
WHERE datname = 'mw';
"
```

---

## 2. 컨테이너 관리

### 컨테이너 상태 확인
```bash
docker ps -a --filter "name=mwm" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
```

### mwm-app 재시작
```bash
docker compose restart mwm-app
```

### mwm-app 강제 재생성 (코드 변경 반영)
```bash
docker compose up -d --build --force-recreate mwm-app
```

### 전체 컨테이너 재시작
```bash
docker compose down && docker compose up -d
```

### 특정 컨테이너 로그 확인
```bash
docker logs mwm-app --tail 100 -f
```

---

## 3. gunicorn 관련

### 컨테이너 내부에서 gunicorn 중지
```bash
docker exec mwm-app sh -c "pkill gunicorn"
# 강제 종료
docker exec mwm-app sh -c "pkill -9 gunicorn"
```

### gunicorn 프로세스 확인
```bash
docker exec mwm-app ps aux | grep gunicorn
```

---

## 4. Kroki (Mermaid 다이어그램) 서비스

### Kroki 컨테이너 시작
```bash
docker compose up -d mwm-kroki mwm-kroki-mermaid
```

### Kroki 연결 테스트
```bash
docker exec mwm-app sh -c "wget -qO- http://mwm-kroki:8000/health || echo 'FAILED'"
```

---

## 5. Redis 관련

### Redis 연결 테스트
```bash
docker exec mwm-redis redis-cli ping
# → PONG 이면 정상
```

### Redis 데이터 초기화 (주의!)
```bash
docker exec mwm-redis redis-cli FLUSHALL
```

---

## 6. DB 테이블 owner 일괄 변경

`InsufficientPrivilege` 오류 시 모든 테이블의 owner를 `tiffanie`로 변경.

```bash
docker exec mwm-db psql -U postgres -d mw -c "
SELECT 'ALTER TABLE ' || tablename || ' OWNER TO tiffanie;'
FROM pg_tables 
WHERE schemaname = 'public' AND tableowner = 'postgres';
"
# 위 출력 결과를 복사하여 실행
```

---

## 7. 빠른 진단 체크리스트

| 순서 | 확인 항목 | 명령어 |
|------|----------|--------|
| 1 | 컨테이너 상태 | `docker ps -a --filter "name=mwm"` |
| 2 | 앱 로그 | `docker logs mwm-app --tail 50` |
| 3 | DB 연결 | `docker exec mwm-db psql -U postgres -d mw -c "SELECT 1;"` |
| 4 | DB 세션 | 위 §1의 활성 세션 확인 명령 |
| 5 | Redis 연결 | `docker exec mwm-redis redis-cli ping` |
| 6 | 테이블 owner | `docker exec mwm-db psql -U postgres -d mw -c "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' AND tableowner!='tiffanie';"` |
