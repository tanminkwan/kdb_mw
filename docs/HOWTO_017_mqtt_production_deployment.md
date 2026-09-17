# HOWTO_017: MQTT 실시간 Command — 프로덕션 적용 절차

기능 설계·검증 내용은 [HOWTO_016](HOWTO_016_mqtt_realtime_command.md) 에 있다.
이 문서는 **이미 구현된 기능을 프로덕션에 옮기는 작업 목록**만 다룬다.

적용 대상은 3가지다. 그 외 파일(`docs/*`, `README.md`, `.env.example`,
`migrations/*`, `requirements.txt`)은 이미지에 들어가지 않으므로 빌드에 불필요하다.

1. DB enum 라벨 추가 (§1)
2. mwm-app 이미지에 포함할 소스 (§2)
3. `config.py` / `docker-compose.yml` (§3, §4)

---

## 1. DB — 코드 배포보다 **먼저** 적용한다

```sql
ALTER TYPE commandstatusenum ADD VALUE IF NOT EXISTS 'MQTT';
ALTER TYPE commandstatusenum ADD VALUE IF NOT EXISTS 'MQTT_FAILED';
ALTER TYPE targettosendenum  ADD VALUE IF NOT EXISTS 'MQTT';
```

라벨 추가만으로 테이블 rewrite 가 없어 무중단이며, `IF NOT EXISTS` 라 재실행도 안전하다.
타입 소유자(`tiffanie`) 또는 superuser 로 실행한다.

### 순서를 지켜야 하는 이유

`app/sqls/agent.py` 의 미수행 판정이 `command_status.in_(['CREATE', 'MQTT', 'KAFKA'])`
로 바뀌었고, 이 쿼리는 `create_command_detail()` 안에 있어 **모든 명령 생성 시** 실행된다.
`command_sender` 가 SERVER/KAFKA 든, `MQTT_ENABLED=False` 든 무조건이다.
`command_status` 는 native enum(`Column(Enum(CommandStatusEnum))`) 이므로 DB 에 라벨이
없으면 다음 오류로 **MQTT 와 무관하게 명령 생성이 전면 실패**한다.

```
ERROR:  invalid input value for enum commandstatusenum: "MQTT"
```

### 하지 말 것

- **`SERVER_N_MQTT` 추가 금지.** 코드가 채택하지 않은 값이다
  (`app/models/common.py` — push/polling 이중 실행 위험으로 도입 보류).
- **`flask db upgrade` 사용 금지.** 마이그레이션 파일 `b7c1d9e4f2a8` 의
  `down_revision` 은 `a1b2c3d4e5f6` 다. 프로덕션 `alembic_version` 이 다르면
  의도치 않은 마이그레이션이 함께 돌거나 실패한다. 위 SQL 을 수동 적용한다
  (HOWTO_015 §3.2 와 동일한 방식).

적용 확인:

```sql
SELECT t.typname, string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder)
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
WHERE t.typname IN ('commandstatusenum', 'targettosendenum')
GROUP BY t.typname;
```

---

## 2. mwm-app 이미지에 포함할 소스 (10개)

`Dockerfile.app` 은 `COPY app app` / `COPY config.py config.py` 만 수행한다.
빌드 컨텍스트에 아래 파일이 반영돼 있어야 한다.

### 신규

```
app/mqtt/__init__.py
app/mqtt/mqtt_publisher.py
```

`app/mqtt/` 는 디렉터리째로 신규다. 누락되면 `app/__init__.py` 의
`from .mqtt import init_publisher` 에서 **ImportError 로 앱이 기동하지 않는다**
(이 import 는 try 로 감싸져 있지 않다).

### 수정

```
app/__init__.py                                 퍼블리셔 초기화 호출
app/models/common.py                            enum 확장 + 상태 색상 매핑
app/views/agent.py                              periodic_type IMMEDIATE 강제, after_commit 훅
app/sqls/agent.py                               발송 분기, commit 이후 발행, 미수행 가드
app/api/agent_api.py                            BOOT 핸드셰이크
app/templates/agent/command_master_add.html     MQTT 선택 시 실행구분 고정/비활성
app/templates/agent/command_master_edit.html    동일
config.py                                       §3
```

---

## 3. config.py

파일 맨 끝(`IDP_CLIENT_SECRET` 행 다음)에 추가한다. 기존 행의 수정·삭제는 없다.

```python
# ---------------------------------------------------
# MQTT (실시간 Command 발송)
# ---------------------------------------------------
MQTT_ENABLED = os.getenv('MQTT_ENABLED', 'False').lower() in ('true', '1', 'yes')
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', 'central')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_CLIENT_ID_PREFIX = os.getenv('MQTT_CLIENT_ID_PREFIX', 'controller')
MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', '60'))
MQTT_RECONNECT_DELAY = int(os.getenv('MQTT_RECONNECT_DELAY', '60'))
MQTT_LOG_THROTTLE_SECONDS = int(os.getenv('MQTT_LOG_THROTTLE_SECONDS', '3600'))
MQTT_CMD_TOPIC = os.getenv('MQTT_CMD_TOPIC', 'cmd/{agent_id}/req')
MQTT_BROADCAST_TOPIC = os.getenv('MQTT_BROADCAST_TOPIC', 'cmd/broadcast/req')
MQTT_QOS = int(os.getenv('MQTT_QOS', '1'))
MQTT_MESSAGE_EXPIRY = int(os.getenv('MQTT_MESSAGE_EXPIRY', '3600'))
MQTT_PUBLISH_TIMEOUT = float(os.getenv('MQTT_PUBLISH_TIMEOUT', '5'))
```

14줄을 모두 넣는다. 아래 5개는 코드에서 `config['키']` 로 직접 읽어 누락 시 KeyError 다.

| 변수 | 사용처 |
|---|---|
| `MQTT_CMD_TOPIC` | `app/sqls/agent.py` — MQTT 명령 발행 토픽 조립 |
| `MQTT_BROADCAST_TOPIC`, `MQTT_QOS` | `app/api/agent_api.py` — Agent BOOT 응답 |
| `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT` | `app/api/agent_api.py`, `app/mqtt/__init__.py` |

나머지는 `app/mqtt/__init__.py` 에서 `.get(키, 기본값)` 으로 읽으므로 누락돼도 동작하지만,
기본값을 한곳에서 관리하기 위해 함께 둔다.

`import os` 는 파일 상단에 이미 있어 추가 import 가 필요 없다.

---

## 4. docker-compose.yml

`mwm-app` 의 `environment:` 에 5개를 넣는다.

```yaml
      MQTT_ENABLED: "False"                 # 1차 배포는 False (§5)
      MQTT_BROKER_HOST: <프로덕션 브로커 주소>
      MQTT_BROKER_PORT: "1883"
      MQTT_USERNAME: central
      MQTT_PASSWORD: "<central 비밀번호>"
```

- `MQTT_ENABLED` / `MQTT_BROKER_PORT` 는 **따옴표 필수**다. 없으면 compose 가 bool/int 로
  파싱해 `services.mwm-app.environment` 타입 오류가 난다.
- `MQTT_BROKER_HOST` 에 **`172.26.0.1` 을 그대로 쓰지 않는다.** 개발 환경의
  `mw_app_default` 브리지 게이트웨이 IP 이며, 프로덕션에서는 다른 대상을 가리킬 수 있다.
  `docker network inspect <네트워크> --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'`
  로 확인하거나, 브로커가 같은 네트워크에 있으면 컨테이너명을 쓴다.
- `.env` 를 쓰지 않는 환경에서는 `${MQTT_ENABLED:-False}` 형태의 치환을 쓰지 않는다.
  값이 항상 기본값으로 굳는다.
- 이 5개는 환경변수이므로 **값 변경에 재빌드가 필요 없다.** `docker compose up -d mwm-app`
  재기동만으로 켜고 끈다. 재빌드가 필요한 건 `config.py` 자체를 고칠 때다.

---

## 5. 적용 순서

MQTT 를 처음부터 켜지 않고 2단계로 나누면 문제 원인 분리와 롤백 판단이 쉽다.

### Phase 1 — DB + 코드만 (`MQTT_ENABLED=False`)

1. §1 SQL 적용 및 확인
2. §2 파일 반영, §3 `config.py`, §4 `docker-compose.yml` (`MQTT_ENABLED: "False"`)
3. `docker compose build mwm-app` → `docker compose up -d mwm-app`
4. 검증
   - 로그에 `MQTT 비활성화 (MQTT_ENABLED=False) - REST 폴링만 사용`
   - 기존 명령 생성·수행 정상
   - 이미지 확인: `docker run --rm --entrypoint sh mwm-app -c "ls app/mqtt"`

이 상태의 기능 변화는 하나다. 미수행 판정에 `KAFKA`/`MQTT` 가 포함되어, 이전에는
status `KAFKA` 인 건에 상세가 중복 생성되던 것이 이제 생략된다. KAFKA 발송을 쓰는
환경이면 이 변화를 먼저 확인한다.

### Phase 2 — 켜기

5. `MQTT_ENABLED: "True"` 로 바꾸고 `docker compose up -d mwm-app` (재빌드 없음)
6. 로그에서 CONNACK Success 확인
7. 테스트 Agent 1대에 `command_sender=MQTT` 로 1건 → `ag_command_detail.command_status`
   가 `MQTT` 로 올라가고 결과가 수초 내 `COMPLITED` 인지 확인
8. 확대

> `MQTT_PASSWORD` 가 비어 있으면 `MQTT_ENABLED=True` 여도 경고 후 자동 비활성화된다
> (`app/mqtt/__init__.py`). "켠 줄 알았는데 안 켜진" 상태가 되므로 로그를 확인한다.

---

## 6. 롤백

코드 롤백 전에 DB 를 정리한다. 구버전 모델에는 `MQTT` enum 멤버가 없어, 해당 값이 든
행을 읽는 순간 SQLAlchemy 가 `LookupError` 를 낸다.

```sql
UPDATE ag_command_master SET command_sender = 'SERVER' WHERE command_sender = 'MQTT';
UPDATE ag_command_detail SET command_status = 'CREATE'
 WHERE command_status IN ('MQTT', 'MQTT_FAILED');
```

- 위 UPDATE 를 빼먹으면 구버전 가드(`command_status == 'CREATE'`)가 status `MQTT` 인 행을
  미수행으로 보지 않아 상세가 중복 생성되거나, 폴링 쿼리에 잡히지 않아 명령이 영구 대기한다.
- enum 라벨 자체는 PostgreSQL 제약으로 되돌릴 수 없다(마이그레이션 `downgrade()` 도 no-op).
  구버전에 무해하므로 남겨둔다.
