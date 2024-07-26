import requests
import json
from requests.exceptions import ConnectionError

__WAS_STATUS_MESSAGES={
    'RUNNING':'정상'
    ,'SHUTDOWN':'서비스 꺼짐'
    ,'STANDBY':'Application deploy 실패'
    ,'FAILED':'서비스 불가'
    ,'NOTCHECKED':'모니터링 불가'
    ,'UNCHECKED':'Agent 이상'
    }
#################################################################

def getAccessToken(login_url, id, pw):

    data =dict(username=id, password=pw, provider='db', refresh='true')

    headers = {'Content-Type':'application/json;charset=utf-8'}

    access_token = ''
    try:
        resp = requests.post(login_url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            rtn = 1
            access_token = resp.json()['access_token']
        else:
            rtn = -1

    except KeyError:
        rtn = -2
    except ConnectionError:
        rtn = -3

    return rtn, access_token

def getWasStatus(api_url, access_token):

    headers = {'Content-Type':'application/json;charset=utf-8','Authorization':'Bearer '+access_token}

    result = []
    try:
        resp = requests.get(api_url, headers=headers)

        if resp.status_code == 200:
            rtn = 1
            result = resp.json()['list']
        else:
            rtn = -1
    except Exception as e:
        rtn = -2
    
    #print(resp.json())

    return rtn, result

def getNotRunningWasList(status_list):

    result_list = []
    message_list = []
    group_list = []
    was_set = set()

    for r in status_list:
        if r['t__status'] != 'RUNNING':
            result_list.append({'was_id':r['was_id'], 'was_instance_id':r['was_instance_id'], 'status':r['t__status']})
            message_list.append(r['was_id']+'.'+r['was_instance_id']+':'+__WAS_STATUS_MESSAGES[r['t__status']])
            was_set.add(r['was_id'])

    if message_list:
        message_list.sort(key=lambda x: x)

    was_list = [ {'was_id':w,'instances':[]} for w in was_set ]
    for wi in result_list:
        [w['instances'].append({'was_instance_id': wi['was_instance_id'], 'status': wi['status']}) for w in was_list if w['was_id']==wi['was_id']]

    #print('H:',was_list)

    return was_list, ', '.join(message_list)

if __name__ == "__main__":
    
    id = 'agent'
    pw = '1q2w3e4r!!'

    url = 'http://10.0.20.116:5000'
    login_uri = '/api/v1/security/login'
    api_uri = '/api/v1/grid/table/was_status?eql__landscape=PROD'

    rtn, access_token = getAccessToken(url+login_uri, id, pw)

    if rtn == 1:

        rtn, was_status_l = getWasStatus(url+api_uri, access_token)

    if rtn == 1:

        result, message = getNotRunningWasList(was_status_l)
        print(result, message)
