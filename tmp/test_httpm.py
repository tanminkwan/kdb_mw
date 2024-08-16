import requests
import json


#################################################################
data =dict(password='1q2w3e4r!!',username='tiffanie',provider='db',refresh='true')
url = 'http://127.0.0.1:5000'
#url = 'http://10.9.62.162:5000'
headers = {'Content-Type':'application/json;charset=utf-8'}
resp = requests.post(url+'/api/v1/security/login'\
    , data=json.dumps(data), headers=headers)

print('Get access token : ')
print(resp.json())
access_token = resp.json()['access_token']
#################################################################

#xml = 'http_teciaa21.m'
#host_id = 'teciaa21'
#system_user = 'webtob'

#xml = 'http_pgweaa12.m'
#host_id = 'pgweaa12'
#new_yn = 'Y'

#xml = 'http_pmbpwr11c.m'
#host_id = 'pmbpwr11'
#new_yn = 'Y'

#xml = 'http_pmbpwr12c.m'
#host_id = 'pmbpwr12'
#new_yn = 'Y'

#xml = 'ws_engine_urt02a.m'
#host_id = 'urt02a'
#new_yn = 'N'

#xml = 'http_pcbkaa11.m'
#host_id = 'pcbkaa11'
#new_yn = 'Y'

#xml = 'http_pcbkaa12.m'
#host_id = 'pcbkaa12'
#new_yn = 'Y'

#xml = 'http_pcbkaa13.m'
#host_id = 'pcbkaa13'
#new_yn = 'Y'

#xml = 'http_piitpw11.m'
#host_id = 'piitpw11'
#new_yn = 'Y'

xml = 'http_pprmar11.m'
host_id = 'pprmar11'
new_yn = 'Y'
system_user = 'webtob'

#xml = 'http_pprmar12.m'
#host_id = 'pprmar12'
#new_yn = 'Y'

#xml = 'http_piciaa11.m'
#host_id = 'piciaa11'
#new_yn = 'Y'

#xml = 'http_piciaa12.m'
#host_id = 'piciaa12'
#new_yn = 'Y'

fd = open(xml, 'r', encoding='utf-8')
content = fd.read()

data = dict(content=content, host_id=host_id, system_user=system_user)

headers = {'Content-Type':'application/json;charset=utf-8','Authorization':'Bearer '+access_token}
resp = requests.post(url+'/api/v1/config/httpm'\
    , data=json.dumps(data) , headers=headers)

print(resp.json())