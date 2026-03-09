import requests
import os
import json

class MetabaseClient:
    """Metabase API 통신을 위한 재사용 가능한 클라이언트"""
    def __init__(self, url=None, email=None, password=None):
        self.url = url or os.getenv("METABASE_URL", "http://localhost:3000")
        self.email = email or os.getenv("METABASE_ADMIN_EMAIL", "admin@example.com")
        self.password = password or os.getenv("METABASE_ADMIN_PASSWORD", "Password123!")
        self.session_id = None
        self.headers = {}

    def authenticate(self):
        """세션 ID 획득 및 인증 헤더 설정"""
        try:
            res = requests.post(f"{self.url}/api/session", json={"username": self.email, "password": self.password})
            if res.status_code == 200:
                self.session_id = res.json().get("id")
                self.headers = {"X-Metabase-Session": self.session_id}
                return True
        except Exception as e:
            print(f"Auth error: {e}")
        return False

    def get_databases(self):
        res = requests.get(f"{self.url}/api/database", headers=self.headers).json()
        return res.get('data', []) if isinstance(res, dict) else res

    def get_cards(self):
        return requests.get(f"{self.url}/api/card", headers=self.headers).json()

    def get_dashboards(self):
        return requests.get(f"{self.url}/api/dashboard", headers=self.headers).json()

    def get_dashboard_detail(self, dashboard_id):
        return requests.get(f"{self.url}/api/dashboard/{dashboard_id}", headers=self.headers).json()

    def update_card(self, card_id, payload):
        res = requests.put(f"{self.url}/api/card/{card_id}", headers=self.headers, json=payload)
        return res.status_code == 200, res.text

    def create_card(self, payload):
        res = requests.post(f"{self.url}/api/card", headers=self.headers, json=payload)
        return res.json() if res.status_code == 200 else None

    def update_dashboard(self, dash_id, payload):
        """대시보드 메타데이터(이름, 파라미터 등) 업데이트"""
        res = requests.put(f"{self.url}/api/dashboard/{dash_id}", headers=self.headers, json=payload)
        return res.status_code == 200, res.text

    def create_dashboard(self, payload):
        res = requests.post(f"{self.url}/api/dashboard", headers=self.headers, json=payload)
        return res.json() if res.status_code == 200 else None

    def update_dashboard_cards(self, dash_id, card_list):
        """Metabase v0.47+ 전용 벌크 대시보드 카드 업데이트 (신규 생성은 음수 ID 사용)"""
        res = requests.put(f"{self.url}/api/dashboard/{dash_id}/cards", headers=self.headers, json={"cards": card_list})
        return res.status_code == 200, res.text

    def add_card_to_dashboard(self, dash_id, card_id):
        # v0.47+ 에서는 PUT /api/dashboard/:id/cards 벌크 처리를 권장하지만, 단일 추가가 필요할 수도 있음.
        # 실제로는 위 bulk 방식을 추천합니다.
        pass
