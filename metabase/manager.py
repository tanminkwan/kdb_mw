import json
import os
import re
from client import MetabaseClient

class MetabaseManager:
    """provisioning.json 명세를 메타베이스에 동기화하는 도구"""
    def __init__(self, config_path=None):
        self.client = MetabaseClient()
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "provisioning.json")
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

    def sync(self):
        """메타베이스 상태를 전체 동기화합니다."""
        if not self.client.authenticate():
            print("Metabase Authentication Failed.")
            return False

        print("\n--- Metabase State Sync Starting ---")
        db_id = self._get_db_id()
        if not db_id: return False

        card_map = self._sync_cards(db_id)
        dash_id = self._sync_dashboard()
        if dash_id:
            self._sync_layout(dash_id, card_map)
        
        print("--- Metabase State Sync Done ---")
        return True

    def _get_db_id(self):
        dbs = self.client.get_databases()
        name = self.config['database']['name']
        db_id = next((d['id'] for d in dbs if d['name'] == name), None)
        if not db_id: print(f"DB '{name}' not found!"); return None
        return db_id

    def _sync_cards(self, db_id):
        print("1. Syncing Cards...")
        existing_cards = self.client.get_cards()
        card_map = {}
        for q_cfg in self.config['questions']:
            # SQL 파라미터 {{...}} 감지 및 Template Tag 자동 생성
            tags = {}
            for tn in re.findall(r"\{\{([a-zA-Z0-9_-]+)\}\}", q_cfg['query']):
                tags[tn] = {"id": tn, "name": tn, "display-name": tn.capitalize(), "type": "text"}
            
            payload = {
                "name": q_cfg['name'], "display": q_cfg['display'], 
                "dataset_query": {"database": db_id, "type": "native", "native": {"query": q_cfg['query'], "template-tags": tags}},
                "visualization_settings": {}
            }
            
            card = next((c for c in existing_cards if c['name'] == q_cfg['name']), None)
            if card:
                self.client.update_card(card['id'], payload)
                cid = card['id']
            else:
                res = self.client.create_card(payload)
                cid = res['id'] if res else None
            if cid: card_map[q_cfg['name']] = cid
        return card_map

    def _sync_dashboard(self):
        print("2. Syncing Dashboard Metadata...")
        dashes = self.client.get_dashboards()
        d_cfg = self.config['dashboard']
        dash = next((d for d in dashes if d['name'] == d_cfg['name']), None)
        params = []
        for p in d_cfg.get('parameters', []):
            p_copy = p.copy()
            if 'id' not in p_copy:
                p_copy['id'] = p_copy.get('slug')
            params.append(p_copy)

        dash_meta = {"name": d_cfg['name'], "parameters": params}
        
        if dash:
            success, msg = self.client.update_dashboard(dash['id'], dash_meta)
            print(f"Update status: {success}, msg: {msg}")
            return dash['id']
        else:
            res = self.client.create_dashboard(dash_meta)
            return res['id'] if res else None

    def _sync_layout(self, dash_id, card_map):
        print("3. Syncing Dashboard Layout & Mappings (v0.47+ Bulk Sync)...")
        detail = self.client.get_dashboard_detail(dash_id)
        p_map = {p['slug']: p['id'] for p in detail.get('parameters', [])}
        
        # Existing dashcards logic
        e_dashcards = {dc['card_id']: dc['id'] for dc in detail.get('dashcards', []) if dc.get('card_id')}

        # Assign negative IDs to new dashcards (to be created)
        next_negative_id = -1
        final_dashcards = []
        
        for c_cfg in self.config['dashboard']['cards']:
            cid = card_map.get(c_cfg['card_name'])
            if not cid: continue

            mappings = []
            for m in c_cfg.get('parameter_mappings', []):
                slug = m['parameter_mapping']
                if slug in p_map:
                    mappings.append({"parameter_id": p_map[slug], "card_id": cid, "target": m['target']})

            item = {
                "card_id": cid, 
                "row": c_cfg['row'], "col": c_cfg['col'], 
                "size_x": c_cfg['size_x'], "size_y": c_cfg['size_y'], 
                "parameter_mappings": mappings, "visualization_settings": {}
            }
            
            # Use existing ID or a fresh negative ID
            if cid in e_dashcards:
                item['id'] = e_dashcards[cid]
            else:
                item['id'] = next_negative_id
                next_negative_id -= 1
            
            final_dashcards.append(item)
            
        success, msg = self.client.update_dashboard_cards(dash_id, final_dashcards)
        if success:
            print("Layout Sync Successful.")
        else:
            print(f"Layout Sync Error: {msg}")

if __name__ == "__main__":
    MetabaseManager().sync()
