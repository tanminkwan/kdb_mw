import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def get_token():
    login_data = {
        "username": "hennry",
        "password": "password",
        "provider": "db"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    return response.json().get('access_token')

def test_batch_api(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. List functions
    print("--- Listing Batch Functions ---")
    res = requests.get(f"{BASE_URL}/api/v1/batch/list", headers=headers)
    print(json.dumps(res.json(), indent=2, ensure_ascii=False))

    # 2. Run createWebtobConn
    print("\n--- Running createWebtobConn ---")
    payload = {
        "params": ["PICI_Domain"] # Example domain_id
    }
    res = requests.post(f"{BASE_URL}/api/v1/batch/run/createWebtobConn", headers=headers, json=payload)
    print(f"Status: {res.status_code}")
    print(json.dumps(res.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    token = get_token()
    if token:
        test_batch_api(token)
    else:
        print("Login failed")
