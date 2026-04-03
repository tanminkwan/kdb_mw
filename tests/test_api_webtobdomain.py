import requests
import json
import os

# Configuration
url = 'http://127.0.0.1:8000'
login_data = dict(password='1q2w3e4r!!', username='tiffanie', provider='db', refresh='true')
headers = {'Content-Type': 'application/json;charset=utf-8'}

# Login to get access token
print('Logging in to get access token...')
try:
    resp = requests.post(url + '/api/v1/security/login', data=json.dumps(login_data), headers=headers)
    resp.raise_for_status()
    login_resp = resp.json()
    access_token = login_resp['access_token']
    print('Login successful.')
except Exception as e:
    print(f'Login failed: {e}')
    exit(1)

# Test Data
httpm_path = '/home/hennry/projects/kdb_mw_20260116/tmp/http_piciaa11.m'
host_id = 'piciaa11'
system_user = 'webtob'

if not os.path.exists(httpm_path):
    print(f'Error: WebToB config file not found at {httpm_path}')
    exit(1)

print(f'Reading WebToB config from {httpm_path}...')
with open(httpm_path, 'r', encoding='utf-8') as fd:
    content = fd.read()

# Prepare request
api_url = url + '/api/v1/config/httpm'
payload = dict(
    content=content,
    host_id=host_id,
    system_user=system_user
)
auth_headers = {
    'Content-Type': 'application/json;charset=utf-8',
    'Authorization': 'Bearer ' + access_token
}

# Send POST request
print(f'Sending POST request to {api_url}...')
try:
    resp = requests.post(api_url, data=json.dumps(payload), headers=auth_headers)
    print(f'Status Code: {resp.status_code}')
    if resp.status_code in [200, 201]:
        print('Response Body:')
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    else:
        print('Error Response Text:')
        print(resp.text)
except Exception as e:
    print(f'API request failed: {e}')
