### 1. ITAM 기준 대사
#### WAS 목록 추출 조건
1. 추출 Table : it_was
2. 필터 조건
- config_status != "불용"
- run_env in ("운영","이관","개발")
- config_name not like "%(S)%"
3. 그룹 조건
- run_env , domain_name 를 key로 동일하면 1개로 취급.
- host_id가 알파벳순으로 처음 것이 대표 host_id로 사용.
4. 추출 정보
- 대표 host_id
- run_env
- domain_name
- install_user
- was_ssl_yn
- os_type
- config_name
- config_id
5. 오류 항목 및 추출 조건
- `hostname 등록 여부`
host_id not in (select host_id from mw_server where use_yn = "YES")
- `미등록 WAS`
domain_name, run_env 를 key로 사용 
not in (select was_id, landscape from mw_was)
run_env -> mw_was.landscape 변환 해서 비교
- `설치 서버 다름`
host_id != mw_was.located_host_id

#### 내장 WEB 추출 조건
1. 추출 Table : it_was
2. 필터 조건
- config_status != "불용"
- run_env in ("운영","이관","개발")
- config_name not like "%(S)%"
- embed_web_yn = "Y"
3. 추출 정보
- host_id
- run_env
- domain_name
- install_user
- os_type
- config_name
- config_id
- embed_web_port
- embed_web_ssl_yn
4. 오류 항목 및 추출 조건
- `미등록 WEB`
host_id, embed_web_port 를 key로 사용 
not in (select host_id, port from mw_web)
- `SSL 여부 다름`
embed_web_ssl_yn != mw_web.t__ssl_yn
embed_web_ssl_yn -> t__ssl_yn 변환 해서 비교
- `운용환경 다름`
run_env != mw_web.landscape
run_env -> landscape 변환 해서 비교
- `내장 웹 여부 다름`
mw_web.built_type != "내장"
- `WAS Domain 다름`
domain_name != mw_web.dependent_was_id

#### WEB 추출 조건
1. 추출 Table : it_web
2. 필터 조건
- config_status != "불용"
- run_env in ("운영","이관","개발")
- config_name not like "%(S)%"
3. 추출 정보
- host_id
- run_env
- domain_name
- install_user
- os_type
- config_name
- config_id
- node_port
- ssl_yn
- webtob_version
4. 오류 항목 및 추출 조건
- `미등록 WEB`
host_id, node_port 를 key로 사용 
not in (select host_id, port from mw_web)
- `SSL 여부 다름`
ssl_yn != mw_web.t__ssl_yn
ssl_yn -> t__ssl_yn 변환 해서 비교
- `운용환경 다름`
run_env != mw_web.landscape
run_env -> landscape 변환 해서 비교
