# Metabase 임베딩(Embedding) 가이드

이 문서는 Metabase 대시보드를 Static Embedding (JWT 기반 보안 임베딩) 방식을 사용하여 mw-app (Flask-AppBuilder) 메뉴 내에 통합하는 방법을 설명합니다.

### 1단계: Metabase 관리자 페이지에서 임베딩 활성화 및 Secret Key 확인
1. Metabase 로그인 후 우측 상단 톱니바퀴 > **[Admin settings]** (관리자 설정)으로 이동합니다.
2. 좌측 메뉴에서 **[Embedding]** > **[Custom Embedding]**을 선택합니다.
3. 임베딩 기능을 **활성화(Enable)** 합니다.
4. 화면에 생성된 아주 긴 길이의 **`Metabase Secret Key`** 값을 복사하여 보관합니다.
5. 임베딩 하고자 하는 대시보드(Dashboard) 화면으로 이동하여 오른쪽 위의 공유 아이콘 > **[Embedding]**을 클릭합니다. 나타나는 안내 화면 코드상에서 해당 대시보드의 **Dashboard ID**(숫자)를 확인합니다.

### 2단계: Python 라이브러리 추가
서명된 토큰(JWT)을 만들기 위해 라이브러리가 필요합니다. `mw_app/requirements.txt`에 다음을 추가하고 설치해줍니다.
*(이미 설치되어 있다면 이 단계는 건너뛰어도 됩니다.)*
```txt
PyJWT==2.8.0
```

### 3단계: 환경변수 및 설정 추가 (`config.py`)
Flask 앱의 설정(config) 파일에 다음과 같이 Metabase 연동 설정값들을 추가합니다.
```python
# config.py 하단 쯤에 추가

METABASE_SITE_URL = "http://mwm-metabase:3000"  # 또는 실제 띄울 Nginx 도메인 URL
METABASE_SECRET_KEY = "1단계에서 복사한 아주 긴 시크릿 키 문자열"
METABASE_DASHBOARD_ID = 1  # 1단계에서 확인한 대시보드 ID 숫자
```

### 4단계: 랜더링할 HTML 템플릿 작성 (`app/templates/metabase_dashboard.html`)
iframe을 띄울 템플릿 파일을 만듭니다. Flask-AppBuilder의 기본 레이아웃을 상속받도록 합니다.
```html
{% extends "appbuilder/base.html" %}

{% block content %}
<div class="container-fluid" style="padding: 0; margin-top: 15px;">
    <!-- 발급받은 iframe url을 src에 동적으로 넣습니다 -->
    <iframe
        src="{{ iframe_url }}"
        frameborder="0"
        width="100%"
        height="800"  <!-- 원하는 높이로 조절 가능 -->
        allowtransparency
    ></iframe>
</div>
{% endblock %}
```

### 5단계: 뷰(View) 및 메뉴 추가 (`app/views/metabase.py` 또는 기존 라우터 파일)
Flask 백엔드에서 10분짜리 단기 JWT 토큰을 만들고, iframe URL에 태워 템플릿으로 렌더링하도록 뷰 클래스를 작성합니다.

```python
from flask import render_template
from flask_appbuilder import BaseView, expose, has_access
import jwt
import time
from app import appbuilder
import config # config.py 임포트

class MetabaseDashboardView(BaseView):
    default_view = 'show_dashboard'

    @expose('/show')
    @has_access
    def show_dashboard(self):
        # 1. JWT 토큰을 위한 페이로드 생성
        payload = {
          "resource": {"dashboard": config.METABASE_DASHBOARD_ID},
          # 대시보드 파라미터가 있다면 아래에 매핑 (예: {"category": "웹서버"})
          "params": {}, 
          "exp": round(time.time()) + (60 * 10) # 토큰 만료시간 (10분 뒤)
        }
        
        # 2. JWT 토큰 암호화 서명
        token = jwt.encode(payload, config.METABASE_SECRET_KEY, algorithm="HS256")
        
        # 3. iframe에 들어갈 URL 완성
        # URL 해시값(#)으로 bordered=true (테두리 보이기), titled=true (타이틀 보이기) 등 옵션과 테마 지정 가능
        iframe_url = f"{config.METABASE_SITE_URL}/embed/dashboard/{token}#bordered=true&titled=true"

        return self.render_template('metabase_dashboard.html', iframe_url=iframe_url)

# 메뉴 트리에 추가 (Dashboard 카테고리 외 원하는 곳에 등록)
appbuilder.add_view(
    MetabaseDashboardView,
    "통계 대시보드",
    icon="fa-bar-chart",
    category="Dashboards",
    category_icon="fa-dashboard"
)
```
