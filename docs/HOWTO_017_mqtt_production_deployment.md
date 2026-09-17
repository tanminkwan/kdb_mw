# HOWTO_017: MQTT 적용 — mwm-app 빌드

MQTT 실시간 Command 기능을 mwm-app 이미지에 반영할 때 복사할 소스와 `config.py`
수정분. 기능 설계는 [HOWTO_016](HOWTO_016_mqtt_realtime_command.md) 참고.

## 1. 복사할 파일 (10개)

`Dockerfile.app` 은 `COPY app app` / `COPY config.py config.py` 만 수행한다.

### 신규

```
app/mqtt/__init__.py
app/mqtt/mqtt_publisher.py
```

`app/mqtt/` 는 디렉터리째로 신규다. 누락되면 `app/__init__.py` 의
`from .mqtt import init_publisher` 에서 ImportError 로 앱이 기동하지 않는다.

### 수정

```
app/__init__.py
app/models/common.py
app/views/agent.py
app/sqls/agent.py
app/api/agent_api.py
app/templates/agent/command_master_add.html
app/templates/agent/command_master_edit.html
config.py
```

### 복사 불필요 (이미지에 들어가지 않음)

```
docs/*  README.md  .env.example  docker-compose.yml  migrations/*  requirements.txt
```

## 2. config.py

파일 맨 끝(`IDP_CLIENT_SECRET` 행 다음)에 추가한다. 기존 행의 수정·삭제는 없다.
`import os` 는 상단에 이미 있다.

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

`MQTT_CMD_TOPIC`, `MQTT_BROADCAST_TOPIC`, `MQTT_QOS`, `MQTT_BROKER_HOST`,
`MQTT_BROKER_PORT` 는 코드에서 `config['키']` 로 직접 읽으므로 누락 시 KeyError 다.

환경마다 다른 값(`MQTT_ENABLED`, `MQTT_BROKER_HOST`, `MQTT_PASSWORD`)은
`docker-compose.yml` 환경변수로 준다. `config.py` 는 이미지로 `COPY` 되므로
여기를 고치면 재빌드가 필요하다.

## 3. 빌드 및 확인

```bash
docker compose build mwm-app
docker compose up -d mwm-app

docker run --rm --entrypoint sh mwm-app -c "ls app/mqtt; grep -c MQTT_ config.py"
#   → __init__.py  mqtt_publisher.py / 14

docker logs mwm-app | grep -i mqtt
#   MQTT_ENABLED=False 면 → MQTT 비활성화 (MQTT_ENABLED=False) - REST 폴링만 사용
```
