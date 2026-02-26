# ITAM 대사(Compare) 기능 구현 계획서

> **작성일**: 2026-02-26  
> **기반 문서**: `docs/itam_compare_requirement.md`

---

## 목차
1. [개요](#1-개요)
2. [기존 코드 구조 분석](#2-기존-코드-구조-분석)
3. [구현 단계](#3-구현-단계)
4. [단계별 상세 계획](#4-단계별-상세-계획)
5. [데이터 변환 규칙](#5-데이터-변환-규칙)
6. [파일 목록 요약](#6-파일-목록-요약)
7. [테스트 계획](#7-테스트-계획)

---

## 1. 개요

ITAM(IT Asset Management) 데이터와 리발소(본 시스템) 데이터 간의 정합성을 비교(대사)하는 기능을 구현한다.

### 대사 유형 (총 6가지)
| 구분 | 기준 | 비교 대상 | 오류 항목 수 |
|------|------|-----------|-------------|
| 1-1 | ITAM WAS (`it_was`) | 리발소 WAS (`mw_was`) | 6가지 |
| 1-2 | ITAM 내장WEB (`it_was`, `embed_web_yn='Y'`) | 리발소 WEB (`mw_web`) | 5가지 |
| 1-3 | ITAM WEB (`it_web`) | 리발소 WEB (`mw_web`) | 6가지 |
| 2-1 | 리발소 WAS (`mw_was`) | ITAM WAS (`it_was`) | 1가지 |
| 2-2 | 리발소 내장WEB (`mw_web`, `built_type='내장'`) | ITAM WAS (`it_was`) | 1가지 |
| 2-3 | 리발소 WEB (`mw_web`, `built_type!='내장'`) | ITAM WEB (`it_web`) | 1가지 |

---

## 2. 기존 코드 구조 분석

### 관련 모델 (현행)
| 파일 | 모델 | 테이블 | 역할 |
|------|------|--------|------|
| `app/models/itam.py` | `ItWas` | `it_was` | ITAM WAS 구성정보 |
| `app/models/itam.py` | `ItWeb` | `it_web` | ITAM WEB 구성정보 |
| `app/models/was.py` | `MwWas` | `mw_was` | 리발소 WAS 도메인 |
| `app/models/was.py` | `MwWeb` | `mw_web` | 리발소 WEB 서버 |
| `app/models/was.py` | `MwWasHttpListener` | `mw_was_httplistener` | WAS HTTP 리스너 (SSL 확인용) |
| `app/models/was.py` | `MwServer` | `mw_server` | 서버 마스터 |
| `app/models/agent.py` | `AgAgent` | `ag_agent` | Agent 정보 (`last_checked_date`) |
| `app/models/common.py` | `LocationEnum` | - | PROD/TEST/DEV/DR |
| `app/models/common.py` | `YnEnum` | - | YES/NO |
| `app/models/common.py` | `BuiltEnum` | - | 외장/내장/분리 |

### 관련 디렉토리 구조
```
app/
├── models/         # 모델 정의 → 신규 모델 추가
│   ├── itam.py     # ItWas, ItWeb (+ 대사결과 모델 추가)
│   └── ...
├── sqls/           # 쿼리 로직 → 대사 쿼리 추가
│   └── (신규) itam_compare.py
├── views/          # 화면 뷰 → 대사 화면 추가
│   └── itam.py     # (기존 + 대사 뷰 추가)
├── api/            # API → 대사 API 추가
│   └── (신규) itam_compare_api.py
└── templates/      # HTML 템플릿 → 대사 결과 화면 추가
    └── (신규) itam_compare.html
```

---

## 3. 구현 단계

```
[Phase 1] 모델 정의 (대사 결과 테이블 4개)
    ↓
[Phase 2] DB 마이그레이션
    ↓
[Phase 3] 데이터 변환 유틸 (run_env ↔ LocationEnum 변환 등)
    ↓
[Phase 4] 대사 로직 (SQL 쿼리 계층)
    ↓
[Phase 5] API 엔드포인트
    ↓
[Phase 6] View & UI
    ↓
[Phase 7] 테스트 & 검증
```

---

## 4. 단계별 상세 계획

### Phase 1. 모델 정의

**파일**: `app/models/itam.py` (기존 파일에 추가)

#### 1-1. `ItItamWasCompare` (ITAM WAS 기준 대사 결과)
```python
class ItItamWasCompare(Model):
    __tablename__ = "it_itam_was_compare"
    
    id            = Column(Integer, primary_key=True, nullable=False)
    config_id     = Column(String(50), ForeignKey('it_was.config_id', ondelete='CASCADE'), nullable=False, comment='ITAM WAS 구성번호')
    error_type    = Column(String(100), nullable=False, comment='오류 항목')
    error_content = Column(Text, comment='오류 내용')
    action_yn     = Column(Enum(YnEnum), info={'enum_class':YnEnum}, server_default=("NO"), comment='조치구분')
    user_id       = Column(String(50), default=get_user, nullable=False)
    create_on     = Column(DateTime(), default=datetime.now, nullable=False)
    
    it_was = relationship('ItWas')
```

> **참고**: 이 테이블은 **ITAM WAS 기준(1-1)**과 **ITAM 내장WEB 기준(1-2)** 대사 결과를 모두 저장한다.

#### 1-2. `ItItamWebCompare` (ITAM WEB 기준 대사 결과)
```python
class ItItamWebCompare(Model):
    __tablename__ = "it_itam_web_compare"
    
    id            = Column(Integer, primary_key=True, nullable=False)
    config_id     = Column(String(50), ForeignKey('it_web.config_id', ondelete='CASCADE'), nullable=False, comment='ITAM WEB 구성번호')
    error_type    = Column(String(100), nullable=False, comment='오류 항목')
    error_content = Column(Text, comment='오류 내용')
    action_yn     = Column(Enum(YnEnum), info={'enum_class':YnEnum}, server_default=("NO"), comment='조치구분')
    user_id       = Column(String(50), default=get_user, nullable=False)
    create_on     = Column(DateTime(), default=datetime.now, nullable=False)
    
    it_web = relationship('ItWeb')
```

#### 1-3. `ItLeebalsoWasCompare` (리발소 WAS 기준 대사 결과)
```python
class ItLeebalsoWasCompare(Model):
    __tablename__ = "it_leebalso_was_compare"
    
    id            = Column(Integer, primary_key=True, nullable=False)
    leebalso_id   = Column(Integer, ForeignKey('mw_was.id', ondelete='CASCADE'), nullable=False, comment='리발소 WAS ID')
    error_type    = Column(String(100), nullable=False, comment='오류 항목')
    error_content = Column(Text, comment='오류 내용')
    action_yn     = Column(Enum(YnEnum), info={'enum_class':YnEnum}, server_default=("NO"), comment='조치구분')
    user_id       = Column(String(50), default=get_user, nullable=False)
    create_on     = Column(DateTime(), default=datetime.now, nullable=False)
    
    mw_was = relationship('MwWas')
```

#### 1-4. `ItLeebalsoWebCompare` (리발소 WEB 기준 대사 결과)
```python
class ItLeebalsoWebCompare(Model):
    __tablename__ = "it_leebalso_web_compare"
    
    id            = Column(Integer, primary_key=True, nullable=False)
    leebalso_id   = Column(Integer, ForeignKey('mw_web.id', ondelete='CASCADE'), nullable=False, comment='리발소 WEB ID')
    error_type    = Column(String(100), nullable=False, comment='오류 항목')
    error_content = Column(Text, comment='오류 내용')
    action_yn     = Column(Enum(YnEnum), info={'enum_class':YnEnum}, server_default=("NO"), comment='조치구분')
    user_id       = Column(String(50), default=get_user, nullable=False)
    create_on     = Column(DateTime(), default=datetime.now, nullable=False)
    
    mw_web = relationship('MwWeb')
```

---

### Phase 2. DB 마이그레이션

```bash
# 마이그레이션 스크립트 생성
flask db migrate -m "add itam compare result tables"

# 마이그레이션 적용
flask db upgrade
```

**생성될 테이블 4개**:
- `it_itam_was_compare`
- `it_itam_web_compare`
- `it_leebalso_was_compare`
- `it_leebalso_web_compare`

---

### Phase 3. 데이터 변환 유틸

**파일**: `app/sqls/itam_compare.py` 상단에 helper 함수로 정의

#### 3-1. `run_env` ↔ `LocationEnum` 변환
```python
# ITAM 운용환경 → 리발소 LocationEnum 변환
RUN_ENV_TO_LOCATION = {
    "운영": "PROD",
    "이관": "TEST",
    "개발": "DEV",
    "DR":   "DR",
}

# 역방향 변환
LOCATION_TO_RUN_ENV = {v: k for k, v in RUN_ENV_TO_LOCATION.items()}

def run_env_to_location(run_env: str) -> str:
    """ITAM run_env를 LocationEnum name으로 변환"""
    return RUN_ENV_TO_LOCATION.get(run_env)

def location_to_run_env(location_name: str) -> str:
    """LocationEnum name을 ITAM run_env로 변환"""
    return LOCATION_TO_RUN_ENV.get(location_name)
```

#### 3-2. SSL 여부 변환
```python
def ssl_yn_to_yn_enum(ssl_yn: str) -> str:
    """ITAM ssl_yn ('Y'/'N') → YnEnum name ('YES'/'NO') 변환"""
    return "YES" if ssl_yn == "Y" else "NO"

def yn_enum_to_ssl_yn(yn_name: str) -> str:
    """YnEnum name ('YES'/'NO') → ITAM ssl_yn ('Y'/'N') 변환"""
    return "Y" if yn_name == "YES" else "N"
```

---

### Phase 4. 대사 로직 (핵심)

**파일**: `app/sqls/itam_compare.py` (신규 생성)

각 대사 유형별로 함수를 작성한다.

#### 4-1. ITAM WAS 기준 대사 (`compare_itam_was`)

```
함수: compare_itam_was() → List[ItItamWasCompare]

1. it_was 데이터 추출
   - 필터: config_status != '불용', run_env in ('운영','이관','개발'), 
           config_name not like '%(S)%', install_user not like 'tmax%'
   - 그룹핑: (run_env, domain_name) 기준, host_id 알파벳순 첫번째가 대표

2. 오류 체크 (6가지):
   a. hostname 미등록
      → host_id가 mw_server(use_yn='YES')에 없는 경우
   b. WAS 미등록
      → (domain_name, run_env→LocationEnum) 조합이 mw_was(was_id, landscape)에 없는 경우
   c. 설치 서버 불일치
      → host_id != mw_was.located_host_id
   d. WAS SSL 불일치
      → mw_was에 소속된 mw_was_httplistener에 ssl_yn='YES'가 존재하면 was_ssl_yn='Y' 여야 함
   e. Agent 없음
      → mw_was.agent_id가 null 또는 빈 문자열
   f. Agent 비활성화
      → ag_agent.last_checked_date가 현재보다 5분 이상 늦은 경우
```

#### 4-2. ITAM 내장WEB 기준 대사 (`compare_itam_embed_web`)

```
함수: compare_itam_embed_web() → List[ItItamWasCompare]

1. it_was 데이터 추출
   - 필터: config_status != '불용', run_env in ('운영','이관','개발'),
           config_name not like '%(S)%', embed_web_yn = 'Y'

2. 오류 체크 (5가지):
   a. 내장 WEB 미등록
      → (host_id, embed_web_port) 조합이 mw_web(host_id, port)에 없는 경우
   b. 내장 WEB SSL 여부 불일치
      → embed_web_ssl_yn 변환값 != mw_web.t__ssl_yn()
   c. 운용환경 불일치
      → run_env 변환값 != mw_web.landscape
   d. 내장 웹 구분 이상
      → mw_web.built_type != '내장' (BuiltEnum.Internal)
   e. WAS Domain 이상
      → domain_name != mw_web.dependent_was_id
```

#### 4-3. ITAM WEB 기준 대사 (`compare_itam_web`)

```
함수: compare_itam_web() → List[ItItamWebCompare]

1. it_web 데이터 추출
   - 필터: config_status != '불용', run_env in ('운영','이관','개발'),
           config_name not like '%(S)%'

2. 오류 체크 (6가지):
   a. hostname 미등록
      → host_id가 mw_server(use_yn='YES')에 없는 경우
   b. WEB 미등록
      → (host_id, node_port) 조합이 mw_web(host_id, port)에 없는 경우
   c. WEB SSL 여부 불일치
      → ssl_yn 변환값 != mw_web.t__ssl_yn()
   d. 운용환경 불일치
      → run_env 변환값 != mw_web.landscape
   e. Agent 없음
      → mw_web.agent_id가 null 또는 빈 문자열
   f. Agent 비활성화
      → ag_agent.last_checked_date가 현재보다 5분 이상 늦은 경우
```

#### 4-4. 리발소 WAS 기준 대사 (`compare_leebalso_was`)

```
함수: compare_leebalso_was() → List[ItLeebalsoWasCompare]

1. mw_was 데이터 추출
   - 필터: use_yn = 'YES'

2. 오류 체크 (1가지):
   a. ITAM 미등록
      → (was_id, landscape→run_env) 조합이 it_was(domain_name, run_env)에 없는 경우
```

#### 4-5. 리발소 내장WEB 기준 대사 (`compare_leebalso_embed_web`)

```
함수: compare_leebalso_embed_web() → List[ItLeebalsoWebCompare]

1. mw_web 데이터 추출
   - 필터: use_yn = 'YES', built_type = '내장' (BuiltEnum.Internal)

2. 오류 체크 (1가지):
   a. ITAM 미등록
      → (host_id, port) 조합이 it_was(host_id, embed_web_port, embed_web_yn='Y')에 없는 경우
```

#### 4-6. 리발소 WEB 기준 대사 (`compare_leebalso_web`)

```
함수: compare_leebalso_web() → List[ItLeebalsoWebCompare]

1. mw_web 데이터 추출
   - 필터: use_yn = 'YES', built_type != '내장' (BuiltEnum.Internal)

2. 오류 체크 (1가지):
   a. ITAM 미등록
      → (host_id, port) 조합이 it_web(host_id, node_port)에 없는 경우
```

#### 4-7. 일괄 대사 실행 함수

```python
def run_all_compare():
    """6가지 대사를 모두 실행하고 결과를 DB에 저장"""
    # 1. 기존 대사 결과 전체 삭제 (truncate)
    # 2. compare_itam_was() 실행 → it_itam_was_compare에 INSERT
    # 3. compare_itam_embed_web() 실행 → it_itam_was_compare에 INSERT
    # 4. compare_itam_web() 실행 → it_itam_web_compare에 INSERT
    # 5. compare_leebalso_was() 실행 → it_leebalso_was_compare에 INSERT
    # 6. compare_leebalso_embed_web() 실행 → it_leebalso_web_compare에 INSERT
    # 7. compare_leebalso_web() 실행 → it_leebalso_web_compare에 INSERT
    # 8. commit
```

#### 4-8. 단건 대사 실행 함수

```python
def compare_single_itam_was(config_id):
    """특정 ITAM WAS config_id에 대한 대사 실행"""
    # 1. 해당 config_id의 기존 대사 결과 삭제
    # 2. 대사 로직 실행
    # 3. 결과 INSERT & commit

def compare_single_itam_web(config_id):
    """특정 ITAM WEB config_id에 대한 대사 실행"""

def compare_single_leebalso_was(was_id):
    """특정 리발소 WAS id에 대한 대사 실행"""

def compare_single_leebalso_web(web_id):
    """특정 리발소 WEB id에 대한 대사 실행"""
```

---

### Phase 5. API 엔드포인트

**파일**: `app/api/itam_compare_api.py` (신규 생성)

| Method | URL | 설명 |
|--------|-----|------|
| `POST` | `/api/v1/itam-compare/run-all` | 일괄 대사 실행 |
| `POST` | `/api/v1/itam-compare/itam-was/<config_id>` | ITAM WAS 단건 대사 |
| `POST` | `/api/v1/itam-compare/itam-web/<config_id>` | ITAM WEB 단건 대사 |
| `POST` | `/api/v1/itam-compare/leebalso-was/<int:id>` | 리발소 WAS 단건 대사 |
| `POST` | `/api/v1/itam-compare/leebalso-web/<int:id>` | 리발소 WEB 단건 대사 |
| `GET`  | `/api/v1/itam-compare/results/itam-was` | ITAM WAS 대사 결과 조회 |
| `GET`  | `/api/v1/itam-compare/results/itam-web` | ITAM WEB 대사 결과 조회 |
| `GET`  | `/api/v1/itam-compare/results/leebalso-was` | 리발소 WAS 대사 결과 조회 |
| `GET`  | `/api/v1/itam-compare/results/leebalso-web` | 리발소 WEB 대사 결과 조회 |

```python
# API 클래스 구조 (Flask-AppBuilder BaseApi 기반)
class ItamCompareApi(BaseApi):
    route_base = "/api/v1/itam-compare"
    
    @expose('/run-all', methods=['POST'])
    def run_all(self):
        """일괄 대사 실행"""
    
    @expose('/itam-was/<config_id>', methods=['POST'])
    def compare_itam_was_single(self, config_id):
        """ITAM WAS 단건 대사"""
    
    # ... 기타 엔드포인트
```

**등록**: `app/__init__.py`에 import 추가
```python
from app.api import ..., itam_compare_api
```

---

### Phase 6. View & UI

#### 6-1. View 클래스 (`app/views/itam.py`에 추가)

```python
class ItamCompareView(BaseView):
    route_base = "/itam_compare"
    default_view = "list"
    
    @expose('/list')
    @has_access
    def list(self):
        """대사 결과 목록 화면"""
        # 4개 탭: ITAM WAS, ITAM WEB, 리발소 WAS, 리발소 WEB
        return self.render_template('itam_compare.html', ...)
```

#### 6-2. ModelView 4개 (대사 결과 테이블별 CRUD 뷰)

```python
class ItItamWasCompareModelView(ModelView):
    datamodel = SQLAInterface(ItItamWasCompare)
    list_title = "ITAM WAS 기준 대사 결과"
    list_columns = ['config_id', 'error_type', 'error_content', 'action_yn', 'create_on']
    label_columns = {
        'config_id': 'ITAM 구성번호',
        'error_type': '오류 항목',
        'error_content': '오류 내용',
        'action_yn': '조치구분',
        'create_on': '생성일시'
    }

class ItItamWebCompareModelView(ModelView):
    # 동일 패턴

class ItLeebalsoWasCompareModelView(ModelView):
    # leebalso_id 기준

class ItLeebalsoWebCompareModelView(ModelView):
    # leebalso_id 기준
```

#### 6-3. 메뉴 등록

```python
# 지식관리 오른쪽에 'ITAM 대사' 카테고리 메뉴 추가
appbuilder.add_view(
    ItItamWasCompareModelView,
    "ITAM WAS 기준 대사",
    icon="fa-exchange",
    category="ITAM 대사"
)
appbuilder.add_view(
    ItItamWebCompareModelView,
    "ITAM WEB 기준 대사",
    icon="fa-exchange",
    category="ITAM 대사"
)
appbuilder.add_view(
    ItLeebalsoWasCompareModelView,
    "리발소 WAS 기준 대사",
    icon="fa-exchange",
    category="ITAM 대사"
)
appbuilder.add_view(
    ItLeebalsoWebCompareModelView,
    "리발소 WEB 기준 대사",
    icon="fa-exchange",
    category="ITAM 대사"
)

# 대사 실행 화면 (일괄 실행 버튼 포함)
appbuilder.add_view(
    ItamCompareView,
    "대사 실행",
    icon="fa-play",
    category="ITAM 대사"
)
```

#### 6-4. 템플릿 (`app/templates/itam_compare.html`)

```
- 상단: "일괄 대사 실행" 버튼
- 4개 탭 구성:
  1. ITAM WAS 기준 대사 결과
  2. ITAM WEB 기준 대사 결과
  3. 리발소 WAS 기준 대사 결과
  4. 리발소 WEB 기준 대사 결과
- 각 탭: 대사 결과 테이블 (오류 항목, 오류 내용, 조치구분 등)
- 조치구분 컬럼: 인라인 수정 가능 (YES/NO 토글)
```

---

## 5. 데이터 변환 규칙

### 5-1. `run_env` → `LocationEnum` 매핑
| ITAM `run_env` | 리발소 `LocationEnum` |
|---|---|
| 운영 | PROD |
| 이관 | TEST |
| 개발 | DEV |
| DR | DR |

### 5-2. SSL 여부 매핑
| ITAM `ssl_yn` | 리발소 비교 |
|---|---|
| `Y` | `mw_web.ssl_object`가 존재 → `t__ssl_yn()` = `'YES'` |
| `N` | `mw_web.ssl_object`가 미존재 → `t__ssl_yn()` = `'NO'` |

### 5-3. WAS SSL 비교 로직
```
mw_was_httplistener에서 해당 was_id의 레코드 중 ssl_yn = 'YES'인 것이 있으면:
  → it_was.was_ssl_yn = 'Y' 여야 정상
없으면:
  → it_was.was_ssl_yn = 'N' 여야 정상
```

### 5-4. Agent 비활성화 판단
```
현재시간 - ag_agent.last_checked_date > 5분 (300초)
```

---

## 6. 파일 목록 요약

### 신규 생성
| 파일 | 용도 |
|------|------|
| `app/sqls/itam_compare.py` | 대사 로직 (6가지 대사 함수 + 변환 유틸) |
| `app/api/itam_compare_api.py` | REST API 엔드포인트 |
| `app/templates/itam_compare.html` | 대사 실행 & 결과 조회 화면 |

### 수정
| 파일 | 변경 내용 |
|------|-----------|
| `app/models/itam.py` | 대사 결과 모델 4개 추가 (`ItItamWasCompare`, `ItItamWebCompare`, `ItLeebalsoWasCompare`, `ItLeebalsoWebCompare`) |
| `app/views/itam.py` | 대사 결과 ModelView 4개 + `ItamCompareView` 추가, 메뉴 등록 |
| `app/__init__.py` | `from app.sqls import ... itam_compare` 및 `from app.api import ... itam_compare_api` 추가 |

---

## 7. 테스트 계획

### 7-1. 단위 테스트
| 테스트 항목 | 내용 |
|---|---|
| 변환 함수 | `run_env_to_location`, `location_to_run_env`, `ssl_yn_to_yn_enum` |
| ITAM WAS 필터 | 불용/운영환경/(S) 필터 정상 동작 확인 |
| 그룹핑 로직 | (run_env, domain_name) 그룹핑, 대표 host_id 선정 |
| 각 오류 유형 | 오류 조건별 개별 테스트 |

### 7-2. 통합 테스트
| 테스트 항목 | 내용 |
|---|---|
| 일괄 대사 | `run_all_compare()` 실행 후 4개 테이블에 결과 정상 저장 확인 |
| 단건 대사 | 특정 config_id/id에 대한 대사 결과 확인 |
| API 호출 | 각 API 엔드포인트 정상 응답 확인 |
| UI 확인 | 메뉴 표시, 탭 전환, 결과 목록 표시, 조치구분 수정 |

### 7-3. 검증 시나리오
```
1. ITAM 데이터에 존재하지만 리발소에 없는 WAS → "WAS 미등록" 오류
2. 리발소에 존재하지만 ITAM에 없는 WAS → "ITAM 미등록" 오류
3. SSL 설정 불일치 케이스 → 해당 SSL 불일치 오류
4. Agent 연결 끊긴 WAS → "Agent 비활성화" 오류
5. 정상 데이터 → 오류 레코드 미생성 확인
```

---

## 구현 우선순위

| 순서 | Phase | 예상 시간 | 비고 |
|------|-------|-----------|------|
| 1 | Phase 1 (모델) | 30분 | 모델 4개 추가 |
| 2 | Phase 2 (마이그레이션) | 15분 | flask db migrate/upgrade |
| 3 | Phase 3 (변환 유틸) | 20분 | 헬퍼 함수 |
| 4 | Phase 4 (대사 로직) | 2~3시간 | **핵심 로직**, 6가지 대사 함수 |
| 5 | Phase 5 (API) | 1시간 | REST API |
| 6 | Phase 6 (View & UI) | 1~2시간 | 화면, 메뉴 |
| 7 | Phase 7 (테스트) | 1시간 | 검증 |

**총 예상 소요 시간**: 약 6~8시간
