import requests
import json

# Configuration
base_url = 'http://127.0.0.1:8000'
login_url = f'{base_url}/api/v1/security/login'
server_api_url = f'{base_url}/api/v1/mw_server/add'

# Credentials (from other test files)
payload = {
    "username": "tiffanie",
    "password": "1q2w3e4r!!",
    "refresh": True
}

print("Logging in to get access token...")
response = requests.post(login_url, json=payload)

if response.status_code == 200:
    access_token = response.json().get('access_token')
    print("Login successful.")
else:
    print(f"Login failed: {response.status_code}")
    print(response.text)
    exit(1)

# MwServer Data
server_data = {
    "host_id": "piciaa11",
    "server_name": "Test Server piciaa11",
    "landscape": "PROD",
    "os_type": "LINUX",
    "ip_address": "10.0.0.1",
    "use_yn": "YES"
}

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

print(f"Adding server {server_data['host_id']}...")
response = requests.post(server_api_url, headers=headers, json=server_data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
