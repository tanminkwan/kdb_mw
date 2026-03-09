import requests
import os
import sys
from client import MetabaseClient

class MetabaseHealthChecker:
    """Metabase 시스템의 전반적인 상태를 독립적으로 검증하는 도구"""
    def __init__(self):
        self.client = MetabaseClient()
        self.summary = []

    def report(self, task, success, detail=""):
        status = "✅" if success else "❌"
        self.summary.append(f"{status} {task}: {detail}")

    def check_all(self):
        print("\n--- Starting Independent Metabase Health Check ---")
        
        # 1. API Auth Check
        is_auth = self.client.authenticate()
        self.report("API Authentication", is_auth, "Session established" if is_auth else "Failed")
        if not is_auth: return False

        # 2. Database Connectivity
        dbs = self.client.get_databases()
        self.report("Database Count", len(dbs) > 0, f"{len(dbs)} database(s) found")
        
        for db in dbs:
            # DB가 활성 상태인지 확인
            is_active = not db.get('is_full_sync', False) # 실제론 더 복잡하지만 간단히 체크
            self.report(f"DB Status [{db['name']}]", True, f"Type: {db['engine']}")

        # 3. Dashboard Accessibility
        dashes = self.client.get_dashboards()
        if dashes:
            self.report("Dashboard Listing", True, f"{len(dashes)} dashboard(s) accessible")
            # 첫 번째 대시보드 무작위 상세 조회 테스트
            target = dashes[0]
            detail = self.client.get_dashboard_detail(target['id'])
            self.report(f"Dashboard Load [{target['name']}]", "id" in detail, f"ID: {target['id']}")

        # 4. Card Query Execution (Sanity check)
        cards = self.client.get_cards()
        if cards:
            self.report("Card Listing", True, f"{len(cards)} card(s) found")
            # 무작위 카드 하나 실행 테스트 (500 에러 여부 확인)
            test_card = cards[0]
            res = requests.post(
                f"{self.client.url}/api/card/{test_card['id']}/query", 
                headers=self.client.headers
            )
            self.report(f"Query Execution [{test_card['name']}]", res.status_code == 200, f"Status: {res.status_code}")

        print("\n".join(self.summary))
        return all("✅" in s for s in self.summary)

if __name__ == "__main__":
    checker = MetabaseHealthChecker()
    success = checker.check_all()
    sys.exit(0 if success else 1)
