from app import appbuilder, app, gitConfig, db
from flask import jsonify, request
from flask_appbuilder import ModelView
from flask_appbuilder.api import BaseApi, expose, safe, rison, protect
from flask_appbuilder.models.sqla.interface import SQLAInterface
from app.models.git import GtGroupUsers
from .common import FilterStartsWithFunction, get_mw_user, get_userid, get_reporttime

import requests
import json
from app.auto_report.testSmtp import send_kdbMail

class GtGroupUsersView(ModelView):
    
    datamodel = SQLAInterface(GtGroupUsers)

    list_title    = "GitLab group id 별 user 매핑"    
    list_columns  = ['group_id', 'user_ids', 'create_on']
    label_columns = {'group_id':'GROUP ID'
                    ,'user_ids':'gitlab user id list'
                     }

    add_columns  = ['group_id', 'user_ids']

    edit_columns  = ['group_id', 'user_ids']

    base_order   = ('create_on', 'desc')

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class GitView(BaseApi):

    resource_name = 'git'

    def getGitUsers(self, group_id):

        rec = db.session.query(GtGroupUsers)\
                    .filter(GtGroupUsers.group_id==group_id).first()
        
        if rec:
            return rec.user_ids
        else:
            return None 

    def getMergeReqeusts(self, iid, project_id, author):

        headers = {'Content-Type':'application/json;charset=utf-8'\
                ,'PRIVATE-TOKEN': gitConfig['giblab_api_private_key']}

        resp = requests.get(gitConfig['api_connection'] + 'merge_requests?scope=all&state=opened&author_id='+str(author), headers=headers)

        if resp.status_code != 200:
            return None, 'GitLab 연계시 Error발생 :' + str(resp.status_code)

        results = resp.json()

        print('KKK : ', results)
        group_user = ''

        for r in results:
            if r['iid']==iid and r['project_id']==project_id:
                if r.get('reviewers'):
                    group_user = r['reviewers'][0]['username']
                else:
                    return None, 'reviewers 정보가 존재하지 않습니다.'

        return group_user, 'OK'

    @expose('/webhook', methods=['POST'])
    def webhook_fromGit(self, **kwargs):

        data = json.loads(request.data)
        
        title       = data['object_attributes']['title']
        url         = data['object_attributes']['url']

        print('HHH2 : ',title)
        author      = data['object_attributes']['author_id']
        iid         = data['object_attributes']['iid']
        description = data['object_attributes']['description']
        description = description.replace('\\n','<br>')

        user_nm   = data['user']['name']
        user_id   = data['user']['username']
        
        project_id   = data['project']['id']
        pjt_id   = data['project']['name']
        pjt_name = data['project']['description']


        print('HHH9 : ',iid, project_id, author)

        group_user, rtn_message = self.getMergeReqeusts(iid, project_id, author)

        if not group_user:
            return self.response_400(message=rtn_message)

        users = self.getGitUsers(group_user)

        print('HHH3 : ',users)

        if not users:
            return self.response_400(message="User가 없음")

        users.split(',')
        host = '10.6.20.40'
        port = 50025
        sender = 'o2000990@gwe.kdb.co.kr'
        sender_name = user_nm
        receivers = [ u+'@gwe.kdb.co.kr' for u in users.split(',')]
        #subject = '[Code Review 알림] Merge Request가 도착하였습니다.'
        subject = '[%s][Merge Request] %s' % (pjt_id, title)
        content = """
    <p style="color: rgb(51, 51, 51); font-family: Dotum, sans-serif, Arial, Gulim, Verdana, 'MS Gothic'; font-size: 17pt;">Merge Request Review 요청입니다.<br>Code Review를 진행해주세요.</p>
    <br>
    <p style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5;"><b>■ 프로젝트 :</b> %s (%s) </p>
    <br>
    <p style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5;"><b>■ 작성자 :</b> %s (%s) </p>
    <br>
    <p style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5;"><b>■ Merge 제목 :</b> %s </p>
    <br>
    <p style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5;"><b>■ Review URL : </b>
    <a href="%s" style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5; color:blue; font-style:italic"> %s </a>
	</p>
    <br>
    <br>
    <p style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5;"><b>■ Merge 내용</b></p>
    <p style="font-size:20px; margin: 0px; padding: 0px; line-height: 1.5;"> %s </p>
    """ % (pjt_name, pjt_id, user_nm, user_id, title , url , url , description)

        print('HHH4 : ',content)
        
        files = []

        send_kdbMail(host, port, sender, sender_name, receivers, subject, content, files)

        return self.response(200)

appbuilder.add_api(GitView)
appbuilder.add_view(
    GtGroupUsersView,
    "Gitlab user group",
    icon="fa-folder-open-o",
    category="Tools",
    category_icon="fa-envelope"
)
appbuilder.add_link(
    name='event.monitoring',
    href='https://mwm-kibana.kdb.co.kr:5601/ui/monitoring.html',
    label="Event 모니터링",
    icon="fa-envelope",
    category="Tools"
)