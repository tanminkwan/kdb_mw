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

        # 1. 카드 동기화 (visualization_settings 포함)
        card_map = self._sync_cards(db_id)
        
        # 2. 대시보드 동기화 (복수 대시보드 대응)
        d_configs = self.config.get('dashboards', [])
        if not d_configs and 'dashboard' in self.config:
            d_configs = [self.config['dashboard']]

        for d_cfg in d_configs:
            dash_id = self._sync_one_dashboard(d_cfg, card_map)
        
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
            tags = {}
            for tn in re.findall(r"\{\{([a-zA-Z0-9_-]+)\}\}", q_cfg['query']):
                tags[tn] = {"id": tn, "name": tn, "display-name": tn.capitalize(), "type": "text"}
            
            payload = {
                "name": q_cfg['name'], "display": q_cfg['display'], 
                "dataset_query": {"database": db_id, "type": "native", "native": {"query": q_cfg['query'], "template-tags": tags}},
                "visualization_settings": q_cfg.get('visualization_settings', {})
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

    def _sync_one_dashboard(self, d_cfg, card_map):
        print(f"2. Syncing Dashboard: {d_cfg['name']}")
        dashes = self.client.get_dashboards()
        dash = next((d for d in dashes if d['name'] == d_cfg['name']), None)
        params = []
        for p in d_cfg.get('parameters', []):
            p_copy = p.copy()
            if 'id' not in p_copy: p_copy['id'] = p_copy.get('slug')
            params.append(p_copy)

        dash_meta = {"name": d_cfg['name'], "parameters": params}
        
        if dash:
            self.client.update_dashboard(dash['id'], dash_meta)
            dash_id = dash['id']
        else:
            res = self.client.create_dashboard(dash_meta)
            dash_id = res['id'] if res else None

        if dash_id:
            self._sync_layout(dash_id, card_map, d_cfg)
        return dash_id

    def _sync_layout(self, dash_id, card_map, d_cfg):
        print(f"3. Syncing Layout for {d_cfg['name']}...")
        detail = self.client.get_dashboard_detail(dash_id)
        p_map = {p['slug']: p['id'] for p in detail.get('parameters', [])}
        e_dashcards = {dc['card_id']: dc['id'] for dc in detail.get('dashcards', []) if dc.get('card_id')}

        next_negative_id = -1
        final_dashcards = []
        
        for c_cfg in d_cfg.get('cards', []):
            cid = card_map.get(c_cfg['card_name'])
            if not cid: continue

            mappings = []
            for m in c_cfg.get('parameter_mappings', []):
                slug = m['parameter_mapping']
                if slug in p_map:
                    mappings.append({"parameter_id": p_map[slug], "card_id": cid, "target": m['target']})

            # 시각화 설정 상속 (Question -> Dashcard)
            base_viz = {}
            target_q = next((q for q in self.config['questions'] if q['name'] == c_cfg['card_name']), None)
            if target_q:
                base_viz = json.loads(json.dumps(target_q.get('visualization_settings', {})))
            base_viz.update(c_cfg.get('visualization_settings', {}))

            item = {
                "card_id": cid, 
                "row": c_cfg['row'], "col": c_cfg['col'], 
                "size_x": c_cfg['size_x'], "size_y": c_cfg['size_y'], 
                "parameter_mappings": mappings, "visualization_settings": base_viz
            }
            
            if cid in e_dashcards:
                item['id'] = e_dashcards[cid]
            else:
                item['id'] = next_negative_id
                next_negative_id -= 1
            
            final_dashcards.append(item)
            
        self.client.update_dashboard_cards(dash_id, final_dashcards)

if __name__ == "__main__":
    MetabaseManager().sync()

if __name__ == "__main__":
    MetabaseManager().sync()
