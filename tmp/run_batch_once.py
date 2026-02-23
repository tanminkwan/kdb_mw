import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def get_token():
    login_data = {
        "username": "tiffanie",
        "password": "1q2w3e4r!!",
        "provider": "db"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/v1/security/login", json=login_data)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"Login failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None

def run_batch(token, function_name, domain_id=''):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "params": [domain_id],
        "command_id": "MANUAL_BATCH_EXEC"
    }
    try:
        url = f"{BASE_URL}/api/v1/batch/run/{function_name}"
        print(f"Calling: {url}")
        res = requests.post(url, headers=headers, json=payload)
        print(f"Status: {res.status_code}")
        print(json.dumps(res.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error running batch: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        # Try both names just in case, but start with the requested one
        run_batch(token, "create_webtob_conn")
    else:
        print("Could not obtain token.")
