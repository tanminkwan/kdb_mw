# HOWTO: CommandMasterApi 사용 가이드

## 1. 개요
이 문서는 `CommandMasterApi`를 사용하여 외부 시스템 등에서 REST API로 즉시 실행 가능한 명령어(`CommandMaster`) 데이터를 생성하는 방법을 안내합니다.

## 2. 엔드포인트 정보
* **경로**: `/api/v1/command_master/create`
* **메서드**: `POST`
* **인증 방식**: Session 및 API Key (Bearer 토큰 지원)

## 3. API Key 인증 방법
API 호출 시 HTTP Header의 `Authorization` 필드에 Bearer 토큰(API Key)을 포함하여 전달해야 합니다.
```bash
curl -X POST "http://<SERVER_IP>:<PORT>/api/v1/command_master/create" \
     -H "Authorization: Bearer <YOUR_API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{...}'
```

## 4. Request Body 파라미터 (JSON)

### 필수 항목
* `command_type_id` (String): 실행할 명령어 타입 ID
* **대상(Target) 지정 (아래 세 가지 중 최소 하나는 반드시 포함)**:
  * `broadcast_callback` (String): 브로드캐스트용 콜백 함수명
  * `target_agent_id` (String 또는 List[String]): 대상 에이전트 ID
  * `target_agent_group_id` (String 또는 List[String]): 대상 에이전트 그룹 ID

### 선택 항목
* `parameters` (String/JSON 객체): 명령어 실행 시 추가적으로 필요한 설정 값

## 5. 요청 예시

### 5.1. 단일/다중 에이전트에 명령어 전달
`target_agent_id`에 문자열 또는 문자열 배열을 전달할 수 있습니다.
```json
{
  "command_type_id": "CMD_UPDATE_CONFIG",
  "target_agent_id": ["AGENT_001", "AGENT_002"],
  "parameters": {
    "module": "nginx",
    "restart": true
  }
}
```

### 5.2. 브로드캐스트(서버 전체)로 콜백 함수 실행
```json
{
  "command_type_id": "CMD_SYNC_STATUS",
  "broadcast_callback": "sync_all_agents",
  "parameters": "{\"force_sync\": true}"
}
```

## 6. Response (응답)

### 6.1. 성공 응답 (HTTP 201)
정상적으로 데이터가 생성된 경우 서버에서 자동 발급한 `command_id`를 반환합니다.
```json
{
  "return_code": 1,
  "message": "OK",
  "command_id": "8b3f2991-c239-45ce-98ea-f03320c4a5da"
}
```

### 6.2. 실패 응답 (HTTP 400 등)
필수 파라미터가 누락된 경우 등에 반환됩니다.
```json
{
  "return_code": -2,
  "message": "Target must be specified (broadcast_callback, target_agent_id, or target_agent_group_id)"
}
```

## 7. 시스템 자동 처리 내역 (DB)
API를 통해 요청된 데이터는 `AgCommandMaster` 테이블에 기록되며, 즉시 실행을 위해 다음 값들이 자동 설정됩니다.
* `periodic_type`: `IMMEDIATE`
* `publish_yn`: `YES`
* `cancel_yn` / `finished_yn`: `NO`
* `command_sender` / `result_receiver`: `SERVER`
* 파라미터로 지정된 대상에 따라 `ag_agent` 및 `ag_agent_group` 연결 매핑 자동 생성 (SQLAlchemy).
