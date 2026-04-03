import requests
import time
import json
import os
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 환경 변수 설정
METABASE_URL = os.getenv("METABASE_URL", "http://mwm-metabase:3000")

session = requests.Session()
if METABASE_URL.startswith("https"):
    session.verify = False

ADMIN_EMAIL = os.getenv("METABASE_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("METABASE_ADMIN_PASSWORD", "Password123!")
DB_HOST = os.getenv("DB_HOST", "mwm-db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mw")
DB_USER = os.getenv("DB_USER", "tiffanie")
DB_PASS = os.getenv("DB_PASS", "1q2w3e4r!!")
ADMIN_FIRST_NAME = os.getenv("METABASE_ADMIN_FIRST_NAME", "Admin")
ADMIN_LAST_NAME = os.getenv("METABASE_ADMIN_LAST_NAME", "User")
SITE_NAME = os.getenv("METABASE_SITE_NAME", "MWM Analytics")
PROVISIONING_FILE = os.getenv("PROVISIONING_FILE", "provisioning.json")

def wait_for_metabase():
    print(f"Waiting for Metabase at {METABASE_URL}...")
    while True:
        try:
            res = session.get(f"{METABASE_URL}/api/health")
            if res.status_code == 200:
                print("Metabase is ready!")
                break
        except:
            pass
        time.sleep(5)

def setup_metabase():
    try:
        res = session.get(f"{METABASE_URL}/api/setup/admin_checklist")
        if res.status_code == 403:
            return authenticate()
    except:
        pass

    print("Initial setup in progress...")
    props = session.get(f"{METABASE_URL}/api/session/properties").json()
    token = props.get("setup-token")
    if not token: return authenticate()

    setup_data = {
        "token": token,
        "user": {
            "first_name": ADMIN_FIRST_NAME,
            "last_name": ADMIN_LAST_NAME,
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        },
        "prefs": {
            "site_name": SITE_NAME,
            "allow_tracking": False
        }
    }
    res = session.post(f"{METABASE_URL}/api/setup", json=setup_data)
    if res.status_code != 200:
        print(f"Initial setup POST /api/setup failed: {res.status_code} - {res.text}")
    
    return authenticate()

def authenticate():
    print(f"Attempting authentication as {ADMIN_EMAIL}...")
    try:
        res = session.post(f"{METABASE_URL}/api/session", json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if res.status_code == 200:
            return res.json().get("id")
        else:
            print(f"Authentication POST /api/session failed: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def provision_resources(session_id):
    headers = {"X-Metabase-Session": session_id}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prov_file_path = os.path.join(script_dir, PROVISIONING_FILE)
    
    if not os.path.exists(prov_file_path):
        print(f"Error: Provisioning file not found at {prov_file_path}")
        return

    with open(prov_file_path, 'r') as f: config = json.load(f)

    # 1. Database Sync
    dbs = session.get(f"{METABASE_URL}/api/database", headers=headers).json()
    if isinstance(dbs, dict): dbs = dbs.get('data', [])
    db_id = next((d['id'] for d in dbs if d['name'] == config['database']['name']), None)

    if not db_id:
        print(f"Adding DB: {config['database']['name']}")
        payload = {
            "name": config['database']['name'], "engine": config['database']['engine'],
            "details": {"host": DB_HOST, "port": int(DB_PORT), "dbname": DB_NAME, "user": DB_USER, "password": DB_PASS, "ssl": False}
        }
        db_id = session.post(f"{METABASE_URL}/api/database", headers=headers, json=payload).json().get("id")

    # 2. Questions (Cards) Sync
    card_map = {}
    existing_cards = session.get(f"{METABASE_URL}/api/card", headers=headers).json()
    for q_cfg in config['questions']:
        card = next((c for c in existing_cards if c['name'] == q_cfg['name']), None)
        
        # SQL 파라미터 {{...}} 감지 및 Template Tag 자동 생성
        tags = {}
        for tn in re.findall(r"\{\{([a-zA-Z0-9_-]+)\}\}", q_cfg['query']):
            # 다시 'text'로 원복하여 데이터 조회 정상화 (Native Query 파라미터 규격)
            tags[tn] = {"id": tn, "name": tn, "display-name": tn.capitalize(), "type": "text"}
            
        payload = {
            "name": q_cfg['name'], "display": q_cfg['display'],
            "dataset_query": {
                "database": db_id, "type": "native", 
                "native": {"query": q_cfg['query'], "template-tags": tags}
            },
            "visualization_settings": q_cfg.get('visualization_settings', {})
        }
        
        if card:
            print(f"Updating question: {q_cfg['name']}")
            res = session.put(f"{METABASE_URL}/api/card/{card['id']}", headers=headers, json=payload)
            if res.status_code != 200:
                print(f"  Failed: {res.status_code} - {res.text}")
            card_id = card['id']
        else:
            print(f"Creating question: {q_cfg['name']}")
            res_card = session.post(f"{METABASE_URL}/api/card", headers=headers, json=payload)
            if res_card.status_code != 200:
                print(f"  Failed: {res_card.status_code} - {res_card.text}")
            card_id = res_card.json().get("id")
        card_map[q_cfg['name']] = card_id

    # 3 & 4. Dashboards Sync
    dashboards = session.get(f"{METABASE_URL}/api/dashboard", headers=headers).json()
    
    for d_cfg in config.get('dashboards', []):
        dash = next((d for d in dashboards if d['name'] == d_cfg['name']), None)
        
        # 파라미터 ID 부여 (Metabase v0.47+ 필수)
        params = []
        for p in d_cfg.get('parameters', []):
            p_copy = p.copy()
            if 'id' not in p_copy: p_copy['id'] = p_copy.get('slug')
            
            if p_copy.get('values_source_type') == 'static-list':
                p_copy['values_query_type'] = 'list'
                p_copy['type'] = 'string/='
                if 'values' in p_copy and 'values_source_config' not in p_copy:
                    p_copy['values_source_config'] = {"values": p_copy.pop('values')}
            params.append(p_copy)

        dash_meta = {"name": d_cfg['name'], "parameters": params}

        if not dash:
            print(f"Creating dashboard: {d_cfg['name']}")
            res = session.post(f"{METABASE_URL}/api/dashboard", headers=headers, json=dash_meta)
            if res.status_code != 200:
                print(f"  Failed to create dashboard: {res.status_code} - {res.text}")
                continue
            dash_id = res.json().get("id")
        else:
            dash_id = dash['id']
            print(f"Updating dashboard metadata for ID {dash_id} ({d_cfg['name']})")
            res = session.put(f"{METABASE_URL}/api/dashboard/{dash_id}", headers=headers, json=dash_meta)
            if res.status_code != 200:
                print(f"  Failed to update dashboard metadata: {res.status_code} - {res.text}")

        # Dashboard Layout & Mappings
        dash_details = session.get(f"{METABASE_URL}/api/dashboard/{dash_id}", headers=headers).json()
        p_map = {p['slug']: p['id'] for p in dash_details.get('parameters', [])}
        e_dashcards = {dc['card_id']: dc['id'] for dc in dash_details.get('dashcards', []) if dc.get('card_id')}

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

            # 질문(Card)에 정의된 기본 시각화 설정을 가져와서 대시보드 카드에 상속
            base_viz = {}
            target_q = next((q for q in config['questions'] if q['name'] == c_cfg['card_name']), None)
            if target_q:
                # 얕은 복사가 아닌 내용 병합을 위해 복사본 사용
                base_viz = json.loads(json.dumps(target_q.get('visualization_settings', {})))
            
            # 대시보드 특정 설정(클릭 동작 등)이 있다면 병합
            dash_card_viz = c_cfg.get('visualization_settings', {})
            base_viz.update(dash_card_viz)

            item = {
                "card_id": cid, "row": c_cfg['row'], "col": c_cfg['col'], 
                "size_x": c_cfg['size_x'], "size_y": c_cfg['size_y'], 
                "parameter_mappings": mappings, 
                "visualization_settings": base_viz
            }
            if cid in e_dashcards: item['id'] = e_dashcards[cid]
            else:
                item['id'] = next_negative_id
                next_negative_id -= 1
            final_dashcards.append(item)
        
        print(f"Updating layout for dashboard: {d_cfg['name']} with {len(final_dashcards)} cards...")
        res = session.put(f"{METABASE_URL}/api/dashboard/{dash_id}/cards", headers=headers, json={"cards": final_dashcards})
        if res.status_code == 200: print(f"Successfully updated {d_cfg['name']}.")
        else: print(f"Failed to update {d_cfg['name']}: {res.status_code} - {res.text}")

if __name__ == "__main__":
    wait_for_metabase()
    sid = setup_metabase()
    if sid:
        provision_resources(sid)
        print("Done!")
    else: print("Failed to log in.")
