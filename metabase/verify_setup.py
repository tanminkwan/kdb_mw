import json
import os
import sys
from client import MetabaseClient

class MetabaseValidator:
    def __init__(self, provisioning_path):
        self.client = MetabaseClient()
        with open(provisioning_path, 'r') as f:
            self.config = json.load(f)
        self.results = []

    def log(self, category, message, success=True):
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append(f"[{category}] {status}: {message}")
        if not success:
            print(f"DEBUG: {message}", file=sys.stderr)

    def verify_all(self):
        if not self.client.authenticate():
            print("Failed to authenticate with Metabase.")
            return False

        print(f"\n--- Verifying Metabase Provisioning State ---")
        self._verify_database()
        self._verify_questions()
        self._verify_dashboard()
        
        print("\n".join(self.results))
        return all("FAIL" not in r for r in self.results)

    def _verify_database(self):
        target_db = self.config['database']['name']
        dbs = self.client.get_databases()
        db = next((d for d in dbs if d['name'] == target_db), None)
        self.log("Database", f"Checking if '{target_db}' exists", db is not None)

    def _verify_questions(self):
        existing_cards = self.client.get_cards()
        for q_cfg in self.config['questions']:
            card = next((c for c in existing_cards if c['name'] == q_cfg['name']), None)
            if not card:
                self.log("Question", f"Question '{q_cfg['name']}' is missing", False)
                continue
            
            # Check if query matches
            dq = card.get('dataset_query', {})
            actual_query = ""
            
            # v0.58+ stages structure
            if 'stages' in dq and len(dq['stages']) > 0:
                stage = dq['stages'][0]
                native = stage.get('native', {})
                if isinstance(native, dict):
                    actual_query = native.get('query', '').strip()
                else:
                    actual_query = str(native).strip()
            # Old structure
            elif 'native' in dq:
                native = dq.get('native', {})
                if isinstance(native, dict):
                    actual_query = native.get('query', '').strip()
                else:
                    actual_query = str(native).strip()
                
            expected_query = q_cfg['query'].strip()
            
            if actual_query != expected_query:
                print(f"DEBUG: '{q_cfg['name']}' query mismatch")
                print(f"  Expected: {repr(expected_query)}")
                print(f"  Actual:   {repr(actual_query)}")
                self.log("Question", f"'{q_cfg['name']}' query mismatch", False)
            else:
                self.log("Question", f"'{q_cfg['name']}' is correctly configured", True)

    def _verify_dashboard(self):
        target_dash = self.config['dashboard']['name']
        dashes = self.client.get_dashboards()
        dash = next((d for d in dashes if d['name'] == target_dash), None)
        
        if not dash:
            self.log("Dashboard", f"Dashboard '{target_dash}' is missing", False)
            return

        detail = self.client.get_dashboard_detail(dash['id'])
        
        # Verify Parameters
        expected_params = self.config['dashboard'].get('parameters', [])
        actual_params = detail.get('parameters', [])
        for ep in expected_params:
            exists = any(ap['slug'] == ep['slug'] for ap in actual_params)
            self.log("Dashboard", f"Filter parameter '{ep['slug']}' exists", exists)

        # Verify Card Count and Layout
        expected_cards = self.config['dashboard']['cards']
        actual_cards = detail.get('dashcards', [])
        self.log("Dashboard", f"Card count (Expected: {len(expected_cards)}, Actual: {len(actual_cards)})", len(expected_cards) == len(actual_cards))

        for ec in expected_cards:
            ac = next((c for c in actual_cards if c.get('card', {}).get('name') == ec['card_name']), None)
            if ac:
                pos_match = (ac['row'] == ec['row'] and ac['col'] == ec['col'])
                self.log("Dashboard", f"Card '{ec['card_name']}' position correct ({ec['row']}, {ec['col']})", pos_match)
                
                # Check mapping
                mappings = ac.get('parameter_mappings', [])
                has_mapping = len(mappings) > 0
                needs_mapping = len(ec.get('parameter_mappings', [])) > 0
                if needs_mapping:
                    print(f"DEBUG: Mapping for {ec['card_name']}: {mappings}")
                    self.log("Dashboard", f"Card '{ec['card_name']}' filter mapping active", has_mapping)
            else:
                self.log("Dashboard", f"Card '{ec['card_name']}' is missing from dashboard", False)

if __name__ == "__main__":
    prov_file = os.path.join(os.path.dirname(__file__), "provisioning.json")
    validator = MetabaseValidator(prov_file)
    success = validator.verify_all()
    sys.exit(0 if success else 1)
