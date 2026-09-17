# HOWTO_017: MQTT 적용 — mwm-app 빌드

## mwm-app 빌드 시 복사할 파일 (10개)

### 신규

```
app/mqtt/__init__.py
app/mqtt/mqtt_publisher.py
```

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

`app/mqtt/` 는 디렉터리째로 신규다. 빠지면 `app/__init__.py:128` 의
`from .mqtt import init_publisher` 에서 ImportError 로 앱이 안 뜬다.

빌드에 불필요(이미지에 안 들어감): `docs/*`, `README.md`, `.env.example`,
`docker-compose.yml`, `migrations/*`, `requirements.txt`

## config.py

맨 끝(`IDP_CLIENT_SECRET` 행 다음)에 추가. 기존 행 수정 없음.

```python
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
