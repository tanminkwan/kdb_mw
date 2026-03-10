# Metabase Provisioning System (v0.58+)

이 문서는 **Metabase v0.58.x** 이상의 환경에서 대시보드를 코드로 관리(`provisioning.json`)하고 자동화된 절차로 동기화 및 검증하는 가이드입니다. 

---

## 🏗 아키텍처 및 핵심 도구

전체 시스템은 **설정(Configuration) - 실행(Execution) - 검증(Verification)**의 3단계로 분리되어 있습니다.

| 파일명 | 역할 및 설명 |
| :--- | :--- |
| **`init.sql`** | Metabase 전용 데이터베이스 인스턴스(`metabase`) 및 접속 계정 권한을 초기 생성하기 위한 수동 실행 DB 스크립트. (`create_db.sql`에 포함된 경우 실행 불필요) |
| **`provisioning.json`** | 대시보드의 **상태 정의서**. SQL 쿼리, 필터 명세, 카드 배치가 JSON으로 정의됨. |
| **`setup.py`** | 최신 Metabase API 규격을 반영한 **현행화 엔진**. 인증 및 리소스 생성을 수행. |
| **`manager.py`** | `provisioning.json`의 내용을 분석하여 Metabase와 **동기화 로직**을 담당하는 핵심 클래스. |
| **`verify_setup.py`** | 명세서(`provisioning.json`)와 실제 Metabase 상태를 비교하여 **성공 여부를 리포트**하는 도구. |
| **`client.py`** | Metabase REST API 통신을 전담하는 공통 클라이언트 (v0.47+ 벌크 API 지원). |
| **`health_check.py`** | 설정값에 의존하지 않고, **Metabase 서비스 자체의 건강 상태**를 점검하는 독립 도구. |

---

## 🛠 표준 작업 절차 (SOP)

### 1단계: 명세서 수정 (`provisioning.json`)
대시보드에 변화를 주고 싶을 때 이 파일을 수정합니다.
*   가로/세로 위치 (`row`, `col`, `size_x`, `size_y`) 조정
*   SQL 쿼리 수정 (변수 사용 시 `{{variable}}` 형식 준수)
*   필터(Parameter) 추가/수정

### 2단계: 리소스 동기화 (`setup.py`)
수정된 명세서를 실제 서버에 반영합니다. 환경변수로 서버 접속 정보를 주입하여 실행합니다.
```bash
# 예시 실행 명령어 (프로젝트 루트 기준)
METABASE_URL=http://localhost:3000 python3 metabase/setup.py
```

### 3단계: 최종 검증 (`verify_setup.py`)
설정이 의도대로 완벽하게 적용되었는지 검증합니다.
```bash
python3 metabase/verify_setup.py
```
*   모든 항목이 **✅ PASS**로 나와야 성공입니다.

---

## 💡 핵심 기술적 포인트 (다른 담당자/AI를 위한 공유)

### 1. 필터 매핑과 500 에러 방지 (ClassCastException)
*   Metabase v0.58+ 에서는 카드를 대시보드 필터와 연결할 때, **카드 자체에 `template-tags`가 사전에 정의**되어 있어야 합니다.
*   `setup.py`는 SQL 쿼리에서 `{{...}}`를 정규식으로 자동 추출하여 이 태그를 생성해 줍니다. 

### 2. 대시보드 카드 벌크 업데이트 (Negative IDs)
*   v0.47 버전부터 단일 카드 추가 API가 제거되었습니다. 대신 `PUT /api/dashboard/:id/cards`로 전체 카드 리스트를 한 번에 보내야 합니다.
*   **중요**: 새로 추가할 카드에는 **음수 ID (`id: -1`, `-2` 등)**를 할당해야 Metabase가 이를 신규 카드로 인식하여 정상 등록합니다.

### 3. 정규화된 쿼리 비교 기법
*   Metabase는 사용자가 입력한 쿼리를 내부적으로 `stages`라는 트리 구조로 저장합니다. 
*   `verify_setup.py`는 이 깊은 계층 구조를 탐색하여 원본 SQL을 정확히 추출하고, 공백을 제거하여 명세서와 비교함으로써 불필요한 실패를 방지합니다.

### 4. 드롭다운 (Static-List) 필터 정의 시 주의사항
*   UI에서 파라미터가 텍스트 박스로 나오는 것을 방지하려면 `provisioning.json`에 선언 시 다음 3가지 필수 구조를 지켜야 합니다.
    1. `type`: `"string/="` 사용 (category, id 등 불가)
    2. `values_query_type`: `"list"` 선언 필수
    3. 실제 데이터 배열은 `values`가 아닌 `values_source_config.values` 내부로 깊게 중첩 선언해야 합니다.
```json
{
  "name": "Landscape", "slug": "landscape", "type": "string/=",
  "values_source_type": "static-list", "values_query_type": "list",
  "values_source_config": { "values": ["전체", "PROD", "DEV", "TEST"] }
}
```

---

## 🚨 문제 해결 (Troubleshooting)

-   **인증 오류**: `METABASE_ADMIN_EMAIL`과 `PASSWORD`가 맞는지 확인하십시오.
-   **필터 연결 실패**: `provisioning.json`의 `parameter_mapping` 이름이 대시보드 `parameters`의 `slug`와 정확히 일치하는지 확인하십시오.
-   **위치 충돌**: 카드 배치 시 좌표가 겹치지 않도록 주의하십시오 (Metabase는 가로 최대 24그리드 시스템을 사용합니다).
