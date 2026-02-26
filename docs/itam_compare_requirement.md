### 1. ITAM 기준 대사
#### 1-1. WAS 목록 추출 조건
1. 추출 Table : it_was
2. 필터 조건
- config_status != "불용"
- run_env in ("운영","이관","개발")
- config_name not like "%(S)%"
- install_user not like "tmax%"
3. 그룹 조건
- run_env , domain_name 를 key로 동일하면 1개로 취급.
- host_id가 알파벳순으로 처음 것이 대표 host_id로 사용.
4. 추출 정보
- 대표 host_id의 config_id
- 대표 host_id
- run_env
- domain_name
- config_name
- install_user
- was_ssl_yn
- os_type
5. 오류 항목 및 추출 조건
- `hostname 미등록`
host_id not in (select host_id from mw_server where use_yn = "YES")
- `WAS 미등록`
domain_name, run_env 를 key로 사용 
not in (select was_id, landscape from mw_was)
run_env -> mw_was.landscape(LocationEnum) 변환 해서 비교
- `설치 서버 불일치`
host_id != mw_was.located_host_id
- `WAS SSL 불일치`
mw_was 에 소속된 mw_was_httplistener.ssl_yn = "YES" 가 존재하면 was_ssl_yn = "Y" 여야 하고 존재하지 않으면 "N" 여야 함.
- `Agent 없음`
domain_name을 key로 사용 
mw_was.agent_id is null or mw_was.agent_id = ''
- `Agent 비활성화`
ag_agent.agent_id = mw_was.agent_id를 만족하는 ag_agent.last_checked_date가 현재보다 5분 이상 늦은 경우

#### 1-2. 내장 WEB 추출 조건
1. 추출 Table : it_was
2. 필터 조건
- config_status != "불용"
- run_env in ("운영","이관","개발")
- config_name not like "%(S)%"
- embed_web_yn = "Y"
3. 추출 정보
- config_id
- host_id
- embed_web_port
- config_name
- embed_web_ssl_yn
- run_env
- domain_name
- install_user
- os_type
4. 오류 항목 및 추출 조건
- `내장 WEB 미등록`
host_id, embed_web_port 를 key로 사용 
not in (select host_id, port from mw_web)
- `내장 WEB SSL 여부 불일치`
embed_web_ssl_yn != mw_web.t__ssl_yn
embed_web_ssl_yn -> t__ssl_yn 변환 해서 비교
- `운용환경 불일치`
run_env != mw_web.landscape
run_env -> landscape(LocationEnum) 변환 해서 비교
- `내장 웹 구분 이상`
mw_web.built_type != "내장"
- `WAS Domain 이상`
domain_name != mw_web.dependent_was_id

#### 1-3. WEB 추출 조건
1. 추출 Table : it_web
2. 필터 조건
- config_status != "불용"
- run_env in ("운영","이관","개발")
- config_name not like "%(S)%"
3. 추출 정보
- config_id
- host_id
- node_port
- config_name
- ssl_yn
- run_env
- install_user
- os_type
- webtob_version
4. 오류 항목 및 추출 조건
- `hostname 미등록`
host_id not in (select host_id from mw_server where use_yn = "YES")
- `WEB 미등록`
host_id, node_port 를 key로 사용 
not in (select host_id, port from mw_web)
- `WEB SSL 여부 불일치`
ssl_yn != mw_web.t__ssl_yn
ssl_yn -> t__ssl_yn 변환 해서 비교
- `운용환경 불일치`
run_env != mw_web.landscape
run_env -> landscape(LocationEnum) 변환 해서 비교
- `Agent 없음`
host_id, node_port 를 key로 사용 
mw_web.agent_id is null or mw_web.agent_id = ''
- `Agent 비활성화`
ag_agent.agent_id = mw_web.agent_id를 만족하는 ag_agent.last_checked_date가 현재보다 5분 이상 늦은 경우

### 2. 리발소 기준 대사
#### 2-1. WAS 목록 추출 조건
1. 추출 Table : mw_was
2. 필터 조건
- use_yn = "YES"
3. 추출 정보
- located_host_id
- landscape
- was_id
- was_name
- sys_user
- c_os_type
4. 오류 항목 및 추출 조건
- `ITAM 미등록`
was_id, landscape 를 key로 사용 
not in (select domain_name, run_env from it_was)
landscape(LocationEnum) -> run_env 변환 해서 비교
#### 2-2. 내장 WEB 추출 조건
1. 추출 Table : mw_web
2. 필터 조건
- use_yn = "YES"
- built_type = "내장" (BuiltEnum)
3. 추출 정보
- host_id
- port
- web_name
- t__ssl_yn
- landscape
- install_user
- mw_server.os_type
- version_info
4. 오류 항목 및 추출 조건
- `ITAM 미등록`
host_id, node_port 를 key로 사용 
not in (select host_id, embed_web_port from it_was where embed_web_yn = "Y")
#### 2-3. WEB 추출 조건
1. 추출 Table : mw_web
2. 필터 조건
- use_yn = "YES"
- built_type != "내장" (BuiltEnum)
3. 추출 정보
- host_id
- port
- web_name
- t__ssl_yn
- landscape
- install_user
- mw_server.os_type
- version_info
4. 오류 항목 및 추출 조건
- `ITAM 미등록`
host_id, node_port 를 key로 사용 
not in (select host_id, node_port from it_web)

### 3. table 정의
#### 3-1. ITAM WAS 기준 대사 결과 테이블
1. it_itam_was_compare
2. 컬럼
- id : int(PK)
- config_id : ITAM WAS 구성번호 (FK) -> it_was.config_id(cascade하게 삭제됨)
- 오류 항목 (대사 구분 2가지(ITAM WAS, ITAM 내장WEB) 해당)
- 오류 내용(text)
- 조치구분(YnEnum)

#### 3-2. ITAM WEB 기준 대사 결과 테이블
1. it_itam_web_compare
2. 컬럼
- id : int(PK)
- config_id : ITAM WEB 구성번호 (FK) -> it_web.config_id(cascade하게 삭제됨)
- 오류 항목
- 오류 내용(text)
- 조치구분(YnEnum)

#### 3-3. 리발소 WAS 기준 대사 결과 테이블
1. table 이름 : it_leebalso_was_compare
2. 컬럼
- id : int(PK)
- leebalso_id : 리발소 WAS 구성번호 (FK) -> mw_was.id(cascade하게 삭제됨)
- 오류 항목
- 오류 내용(text)
- 조치구분(YnEnum)

#### 3-4. 리발소 WEB 기준 대사 결과 테이블
1. table 이름 : it_leebalso_web_compare
2. 컬럼
- id : int(PK)
- leebalso_id : 리발소 WEB 구성번호 (FK) -> mw_web.id(cascade하게 삭제됨)
- 오류 항목
- 오류 내용(text)
- 조치구분(YnEnum)

### 4. UI 정의
1. 지식관리 오른쪽에 `ITAM 대사` 메뉴 추가
2. ITAM 대사 메뉴 클릭시 `ITAM WAS 기준 대사 결과`, `ITAM WEB 기준 대사 결과`, `리발소 WAS 기준 대사 결과`, `리발소 WEB 기준 대사 결과`를 보여주는 화면 추가
### 5. API 정의
1. 일괄작업 기능
2. 특정 한건에 대한 대사 기능
3. 기능은 sql/ 에 view 는 views/ 에 구현