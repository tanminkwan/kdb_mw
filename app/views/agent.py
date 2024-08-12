import logging
from flask import g, render_template, Flask, request, jsonify\
     , send_file, redirect, url_for, render_template_string
from flask_appbuilder.filemanager import FileManager, get_file_original_name
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import BaseView, ModelView, ModelRestApi, MultipleView, MasterDetailView\
    , expose, has_access
from flask_appbuilder.widgets import ListBlock
from flask_appbuilder.actions import action
from flask_appbuilder.api import ModelRestApi, BaseApi, expose, safe, rison, protect
from flask_appbuilder.models.sqla.filters import get_field_setup_query, BaseFilter\
    , FilterEqualFunction, FilterNotEqual,FilterInFunction,FilterStartsWith, FilterEqual
from app import appbuilder, db, scheduler, KAFKA_BROKERS
from app.models.agent import AgCommandType, AgCommandMaster, AgCommandDetail\
    , AgAgentGroup, AgAgent, AgResult, AgFile, AgCommandHelper, AgAutorunResult
from app.dmlsForJeus import JeusDomain, JeusDomainFactory, OldJeusDomain, NewJeusDomain
from app.dmlsForAgent import AutorunResult
from .common import FilterStartsWithFunction, get_mw_user, get_userid\
    , ReadOnlyField, RequiredOnContidion, ValidateBatchFunctionName
from app.sqls.was import getWasInstanceId, getLandscape, getDomainIdAsPK
from app.sqls.agent import checkAgentUpdated, checkAgentAproved\
    , sendCommands, addAgent, addResult, cancelCommands, createCommandDetail_bySch\
    , getLatestFile, updateResultStatus, updateExpiration
from app.file_manager.s3.filemanager import S3FileManager, S3FileUploadField
from sqlalchemy import event

from wtforms import Form, StringField

#from wtforms.fields import TextField
from wtforms.validators import Regexp, EqualTo
from datetime import datetime, timedelta
from app.jobs  import job_ag_create_job
from flask_appbuilder.filemanager import get_file_original_name
import apscheduler
from flask_jwt_extended import create_refresh_token
import sys
from deepdiff import DeepDiff
import json
import xmltodict
"""
@event.listens_for(db.session, 'after_attach')
def test(session, instance):
    print("after_attach : ")

@db.event.listens_for(AgCommandMaster.periodic_type, 'set')
def create_command_detail2(target, value, old_value, initiator):
    print("value :",value)
    print("old_value :",old_value)
    if value.name == 'IMMEDIATE' and old_value != 'IMMEDIATE':
        createCommandDetail(connection, target)
@db.event.listens_for(AgCommandMaster, 'after_update')
def job_after_update_command(mapper, connection, target):
    
    print('Hennry job_after_update_command')
    print(target)
"""
@db.event.listens_for(AgCommandMaster, 'after_insert')
def create_command_detail1(mapper, connection, target):
    
    job_ag_create_job(target)

@db.event.listens_for(AgCommandMaster, 'before_insert')
def set_interval_type(mapper, connection, target):
    
    if target.periodic_type.name != 'PERIODIC':
        target.interval_type = None

@db.event.listens_for(AgFile, 'before_insert')
def set_file_name(mapper, connection, target):
    target.file_name = get_file_original_name(str(target.file))    

class AgentModelView(ModelView):
    
    datamodel = SQLAInterface(AgAgent)
    list_title    = "Agent 현황"
    list_columns  = ['agent_id', 'agent_type', 'agent_version', 'agent_name', 'agent_sub_type','c_last_checked']
    list_template = 'listWithJson.html'
    list_widget = ListBlock
    extra_args = {
        'buttonList':[
         {'text':'PROD','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_landscape=PROD'}
        ,{'text':'DEV','id':'toggle_bt2','bt_group':'1','onclick':'_flt_0_landscape=DEV'}
        ,{'text':'TEST','id':'toggle_bt3','bt_group':'1','onclick':'_flt_0_landscape=TEST'}
        ,{'text':'OffLine','id':'toggle_bt3','bt_group':'1','onclick':'_flt_2_last_checked_date='+(datetime.now() - timedelta(minutes=4)).strftime("%Y-%m-%d+%H:%M:%S")}
        ,{'text':'Not Approved','id':'toggle_bt4','bt_group':'1','onclick':'_flt_0_approved_yn=NO'}
        ],
        'selectList':[
         {'text':'Hostname','id':'host-selector','combind':'0','type':'child'}
        ]
        }
    page_size = 100

    edit_columns = ['agent_id', 'agent_version', 'agent_name', 'landscape', 'agent_sub_type', 'ip_address', 'host_id', 'approved_yn']

    edit_form_extra_fields = {
        'agent_id': StringField('Agent Id', widget=ReadOnlyField())
      , 'agent_version': StringField('Agent Version', widget=ReadOnlyField())
      , 'ip_address': StringField('IP Address', widget=ReadOnlyField())
      , 'host_id': StringField('Host Id', widget=ReadOnlyField())
    }

    base_permissions = ['can_list', 'can_show', 'can_edit']
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class CommandHelperModelView(ModelView):
    
    datamodel = SQLAInterface(AgCommandHelper)
    list_title    = "Command 파라메터 Replace 규칙"
    list_columns  = ['mapping_key','agent_id', 'target_file_name', 'string_to_replace']
    edit_columns  = ['mapping_key','ag_agent', 'target_file_name', 'string_to_replace']
    add_columns  = ['mapping_key','ag_agent', 'target_file_name', 'string_to_replace']
    label_columns = {"target_file_name": "대상 File/기능", "download": "Download"}

class AgentGroupModelView(ModelView):
    
    datamodel = SQLAInterface(AgAgentGroup)
    list_columns  = ['agent_group_id','agent_group_name', 'ag_agent']
    add_columns   = ['agent_group_id','agent_group_name', 'agent_type', 'ag_agent']
    edit_columns  = ['agent_group_id','agent_group_name', 'agent_type', 'ag_agent']
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class FileModelView(ModelView):
    datamodel = SQLAInterface(AgFile)

    label_columns = {"file_name": "File Name", "download": "Download"}
    add_columns   = ['agent_type', 'file_version', 'file']
    edit_columns  = ['agent_type', 'file_version', 'file']
    list_columns  = ['agent_type', 'file_version', 'file_name','download','create_on']
    show_columns  = ['agent_type', 'file_version', 'file', 'file_name','download', 'user_id','create_on']

    validators_columns = {
                'file_version':[Regexp('\d{4}\.\d{4}\.\d{4}', message='format 0000.0000.0000')]
               , 'file_name':[EqualTo('get_filename', message='파일명이 일치하지 않습니다.')]
                }

    edit_form_extra_fields = add_form_extra_fields = {
        "file": S3FileUploadField("S3 File",
                                    description="",
                                    filemanager=S3FileManager,
                                )
    }

    def pre_delete(self, rel_obj):
        filename = getattr(rel_obj, 'file')
        file_obj = S3FileManager()
        file_obj.delete_file(filename)
        
class CommandTypeModelView(ModelView):
    
    datamodel = SQLAInterface(AgCommandType)
    list_title    = "Command Type"
    list_columns  = ['command_type_id', 'command_type_name', 'command_class', 'target_file_name', 'target_file_path']
    label_columns = {'command_type_id':'Command Type Id'
                    ,'command_type_name':'Command Type 설명'
                    ,'command_class':'호출되는 기능'
                    ,'target_file_path':'파일위치(새부기능)'
                    ,'target_file_name':'파일명(기능명)'
                     }
    edit_form_extra_fields = {
        'command_type_id': StringField('Command Type Id', widget=ReadOnlyField())
    }
    edit_columns = ['command_type_id', 'command_type_name', 'command_class', 'target_file_name', 'target_file_path']

    add_columns = ['command_type_id', 'command_type_name', 'command_class', 'target_file_name', 'target_file_path']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    validators_columns = {
                    'target_file_name':[ValidateBatchFunctionName()]
                }

class ResultModelView(ModelView):
    
    datamodel = SQLAInterface(AgResult)
    list_title    = "Command 처리 결과"

    list_template = 'listWithJson.html'
    extra_args = {
        'buttonList':[
         {'text':'WAS 상태','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_key_value1=get_server_stat'}
        ,{'text':'WAS 상태(X)','id':'toggle_bt2','bt_group':'1','onclick':'_flt_4_key_value1=get_server_stat'}
        ,{'text':'domain.xml','id':'toggle_bt3','bt_group':'1','onclick':'_flt_0_key_value1=domain.xml&_flt_1_result_status=NOCHANGE'}
        ,{'text':'JEUSMain.xml','id':'toggle_bt4','bt_group':'1','onclick':'_flt_0_key_value1=JEUSMain.xml&_flt_1_result_status=NOCHANGE'}
        ,{'text':'WEBMain.xml','id':'toggle_bt5','bt_group':'1','onclick':'_flt_0_key_value1=WEBMain.xml&_flt_1_result_status=NOCHANGE'}
        ,{'text':'http.m','id':'toggle_bt6','bt_group':'1','onclick':'_flt_0_key_value1=http.m&_flt_1_result_status=NOCHANGE'}
        ,{'text':'mwmanager','id':'toggle_bt7','bt_group':'1','onclick':'_flt_0_key_value1=mwmanager'}
        ],
        'selectList':[
         {'text':'Hostname','id':'host-selector','combind':'1','type':'child'}
        ,{'text':'Agent ID','id':'agent-selector','combind':'1','type':'child'}
        ],
        'inputList':[
         {'text':'Command ID','id':'command-id','combind':'0','condition':'_flt_3_command_id=','size':15}
        ]
        }

    list_columns  = ['command_id','agent_id', 'repetition_seq', 'host_id', 'key_value1'\
                    , 'colored_result_status', 'sub_result', 'create_on', 'key_value2','complited_date']
    label_columns = {'command_id':'Command ID'
                    ,'agent_id':'Agent ID'
                    ,'repetition_seq':'SEQ'
                    ,'host_id':'HOST ID'
                    ,'key_value1':'파일명(기능명)'
                    ,'key_value2':'파일위치(새부기능)'
                    ,'colored_result_status':'상태'
                    ,'sub_result':'수신정보'
                    ,'create_on':'수신일시'
                    ,'complited_date':'반영일시'
                     }

    edit_columns = ['host_id', 'key_value1', 'key_value2'\
                    , 'result_text', 'result_hash', 'result_status']

    search_columns = ['command_id','agent_id','host_id','key_value1','result_status','create_on']
    base_order = ('create_on', 'desc')
    base_permissions = ['can_list', 'can_show', 'can_edit', 'can_delete']

    formatters_columns={'create_on': lambda x:x.strftime('%Y.%m.%d %H:%M')}
    
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    @action("update_config","Update Config","진짜로?","fa-rocket",single=False)
    def update_config(self, items):

        for result in items:

            if result.result_status.name not in ['CREATE','ERROR']:
                continue

            file_name = result.key_value1
            rtn = 0

            ar = AutorunResult(result=result)

            msg = ''
            if file_name in ['domain.xml','JEUSMain.xml']:
                rtn, msg = ar.updateJeusDomain()
            elif file_name == 'http.m':
                rtn, msg = ar.update_httpm()
            elif file_name == 'WEBMain.xml':
                rtn, msg = ar.updateWebMain()
            elif file_name == 'urlrewrite_config':
                rtn, msg = ar.updateUrlRewrite()
            elif file_name == 'get_server_stat':
                rtn, msg = ar.updateWasStatus()
            elif file_name == 'get_ssl_certi':
                rtn, msg = ar.updateConnectSSLByAPI()
            elif file_name == 'webtob.version.sh':
                rtn, msg = ar.updateWebtobVersion()
            elif file_name == 'webtob.monitor.sh':
                rtn, msg = ar.updateWebtobMonitor()
            elif file_name == 'get_ssl_certifile':
                rtn, msg = ar.update_file_SSL_byAPI()
            elif file_name.startswith('fileSSL.out'):
                rtn, msg = ar.updateFileSSL()
            elif file_name.startswith('connectSSL.out'):
                rtn, msg = ar.updateConnectSSL()
            elif file_name == 'webtob.license.sh' or file_name == 'webtob.license.bat' or file_name.startswith('RUN.WEBTOB.LICENSE.out'):
                rtn, msg = ar.updateWebtobLicenseInfo()
            elif file_name == 'jeus.license.sh' or file_name == 'jeus.license.bat' or file_name.startswith('RUN.JEUS.LICENSE.out'):
                rtn, msg = ar.updateJeusLicenseInfo()
            elif file_name == 'get_find_cmd.sh' or file_name == 'get_find_cmd.bat' or file_name.startswith('RUN.FIND.CMD.out'):
                rtn, msg = ar.updateFilteredInfo()
            elif file_name in ['jeus.properties','jeus.properties.cmd']:
                rtn, msg = ar.updateJeusProperties()
            elif file_name in ['mwmanager.jar','mwmanager4j6.jar','mwmanager4j7.jar']:
                continue
            else:
                rtn = -1
                msg = 'Invalid file_name :' + file_name
            
            ar.updateResultStatus('COMPLITED' if rtn > 0 else 'NOCHANGE' if rtn==0 else 'ERROR', msg)
            
            db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class CommandDetailModelView(ModelView):
    
    datamodel = SQLAInterface(AgCommandDetail)
    list_title    = "Agent별 Command 목록"    

    list_columns  = ['command_id', 'agent_id', 'repetition_seq', 'command_type_id'\
                    , 'command_class', 'target_file_path', 'target_file_name'\
                    , 'additional_params', 'colored_command_status', 'result_received_date']
    label_columns = {'command_id':'Command ID'
                    ,'agent_id':'Agent ID'
                    ,'repetition_seq':'SEQ'
                    ,'command_type_id':'Command Type ID'
                    ,'command_class':'수행기능'
                    ,'colored_command_status':'수행상태'
                    ,'result_received_date':'회신일시'
                     }

    base_permissions = ['can_list', 'can_show', 'can_delete']
    base_order   = ('create_on', 'desc')
    search_columns = ['command_id','agent_id','command_type_id','command_class']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    related_views = [ResultModelView]

class CommandMasterModelView(ModelView):
    
    datamodel = SQLAInterface(AgCommandMaster)

    list_title    = "Command 목록"    
    list_columns  = ['command_id', 'ag_command_type', 'periodic_type', 'ag_agent', 'ag_agent_group'\
                    , 'time_to_exe', 'interval_type', 'cycle_to_exe', 'time_to_stop', 'create_on']
    label_columns = {'command_id':'Command ID'
                    ,'ag_command_type':'Command Type ID'
                    ,'periodic_type':'실행 구분'
                    ,'ag_agent':'대상 Agent'
                    ,'ag_agent_group':'대상 Agent 그룹'
                    ,'time_to_exe':'최초실행일시'
                    ,'interval_type':'실행주기유형'
                    ,'cycle_to_exe':'실행주기(정수)'
                    ,'time_to_stop':'종료일시'
                    ,'additional_params':'Parameters'
                    ,'command_sender':'Command를 보내는 곳'
                    ,'result_receiver':'Result 받는 곳'
                    ,'target_object':'Target Object'
                     }

    add_columns  = ['command_id', 'ag_command_type', 'ag_agent', 'ag_agent_group', 'periodic_type'\
                    , 'command_sender', 'time_to_exe', 'interval_type', 'cycle_to_exe', 'time_to_stop'\
                    , 'additional_params', 'result_receiver','target_object']

    edit_columns  = ['command_id', 'ag_command_type', 'ag_agent', 'ag_agent_group', 'periodic_type'\
                    , 'command_sender', 'time_to_exe', 'interval_type', 'cycle_to_exe', 'time_to_stop'\
                    , 'additional_params', 'cancel_yn']

    base_order   = ('create_on', 'desc')

    validators_columns = {
                    'cycle_to_exe':[RequiredOnContidion('periodic_type', 'PERIODIC', message='주기작업의 경우 필수입력항목입니다.')]
                  , 'time_to_exe':[RequiredOnContidion('periodic_type', 'ONETIME', message='1회성작업의 경우 필수입력항목입니다.')]
                  , 'target_object':[RequiredOnContidion('result_receiver', ['KAFKA','SERVER_N_KAFKA'], message='Result를 KAFKA로 선택한 경우 Target Object에 topic이름을 입력하세요.')]
                  , 'ag_agent':[RequiredOnContidion('ag_agent_group', [[]], message='Agent 또는 Agent 그룹을 선택하세요.')]
                }

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    related_views = [CommandDetailModelView]

class CommandMasterAliveView(ModelView):
    
    datamodel = SQLAInterface(AgCommandMaster)

    list_title    = "활성 Command 목록"    
    list_columns  = ['command_id', 'ag_command_type', 'periodic_type', 'ag_agent', 'ag_agent_group'\
                    , 'time_to_exe', 'interval_type', 'cycle_to_exe', 'time_to_stop', 'create_on']
    label_columns = {'command_id':'Command ID'
                    ,'ag_command_type':'Command Type ID'
                    ,'periodic_type':'실행 구분'
                    ,'ag_agent':'대상 Agent'
                    ,'ag_agent_group':'대상 Agent 그룹'
                    ,'time_to_exe':'최초실행일시'
                    ,'interval_type':'실행주기유형'
                    ,'cycle_to_exe':'실행주기(정수)'
                    ,'time_to_stop':'종료일시'
                    ,'additional_params':'Parameters'
                     }

    base_order   = ('create_on', 'desc')

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user],['finished_yn', FilterEqual, 'NO']]
    base_permissions = ['can_list', 'can_show', 'can_edit']
    related_views = [CommandDetailModelView]

    @action("cancel_commands","Cancel Commands","진짜로?","fa-rocket",single=False)
    def cancel_commands(self, items):

        for cid in items:
            try:
                scheduler.delete_job('CreDetail_'+ cid.command_id)
            except apscheduler.jobstores.base.JobLookupError as e:
                print('cancel_commands : ',e)

        cids = [item.command_id for item in items]
        cancelCommands(cids)
        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class AutorunResultModelView(ModelView):
    
    datamodel = SQLAInterface(AgAutorunResult)

    list_title    = "Result 자동실행 목록"    
    list_columns  = ['autorun_id', 'autorun_type', 'target_file_name', 'command_id'\
                    , 'autorun_func', 'autorun_param', 'create_on']
    label_columns = {'autorun_id':'자동실행 JOB ID'
                    ,'autorun_type':'자동실행 Type'
                    ,'target_file_name':'대상파일/기능'
                    ,'command_id':'Command ID'
                    ,'autorun_func':'자동실행 기능'
                    ,'autorun_param':'Parameter'
                     }

    add_columns  = ['autorun_id', 'autorun_type', 'target_file_name', 'command_id'\
                    , 'autorun_func', 'autorun_param']

    edit_columns  = ['autorun_id', 'autorun_type', 'target_file_name', 'command_id'\
                    , 'autorun_func', 'autorun_param']

    base_order   = ('create_on', 'desc')

    validators_columns = {
                    'target_file_name':[RequiredOnContidion('autorun_type', 'FILENAME', message='대상 File 또는 기능명을 입력하세요.')]
                  , 'command_id':[RequiredOnContidion('autorun_type', 'COMMAND', message='Command ID를 입력하세요.')]
                }

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class CommandApi(BaseApi):

    resource_name = 'command'

    @expose('/<agent_id>/<agent_version>', methods=['GET'])
    @protect()
    def command(self, agent_id, agent_version):
        
        rtn , msg = checkAgentAproved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , msg = checkAgentUpdated(agent_version)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = sendCommands(agent_id, agent_version)

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/<agent_id>/<agent_version>/<agent_type>', methods=['GET'])
    @protect()
    def command_v2(self, agent_id, agent_version, agent_type):
        
        rtn , msg = checkAgentAproved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , msg = checkAgentUpdated(agent_version)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = sendCommands(agent_id, agent_version, agent_type)

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/<agent_id>/<agent_version>/<agent_type>/<agent_status>', methods=['GET'])
    @protect()
    def command_v4(self, agent_id, agent_version, agent_type, agent_status):
        
        rtn , msg = checkAgentAproved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , msg = checkAgentUpdated(agent_version)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = sendCommands(agent_id, agent_version, agent_type)

        #최초 접속인 경우
        if agent_status == 'BOOT':
            data.append(dict(
                        command_class     = 'BOOT',
                        kafka_broker_address = ','.join(KAFKA_BROKERS)
                    ))

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/<agent_id>', methods=['GET'])
    @protect()
    def command_v3(self, agent_id):
        
        rtn , msg = checkAgentAproved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = sendCommands(agent_id)

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/result', methods=['POST'])
    @protect()
    def agent(self, **kwargs):

        data = json.loads(request.data)

        ip_address = request.remote_addr

        if not data.get('agent_id'):
            return jsonify({'return_code':-2,'message':'agent_id does not exist'}), 201
        elif not data.get('command_id'):
            return jsonify({'return_code':-2,'message':'command_id does not exist'}), 201
        elif not data.get('repetition_seq'):
            return jsonify({'return_code':-2,'message':'command_id does not exist'}), 201
        elif not data.get('host_id'):
            return jsonify({'return_code':-2,'message':'host_id does not exist'}), 201
        elif data.get('result_text') == None :
            return jsonify({'return_code':-2,'message':'result_text does not exist'}), 201

        rtn , result_id = addResult(data)

        db.session.commit()

        #Result 상태가 'CREATE' 인 경우 Auto Run Result 수행
        if rtn > 0:

            msg = ''
            try:
                ar = AutorunResult(result_id=result_id)
                rtn2, msg = ar.callAutorunFunc()
            except Exception as e:
                excType, excValue, traceback = sys.exc_info()
                logging.error(f'callAutorunFunc Error : 1{excType} 2{excValue} 3{traceback}')
                rtn2 = -1

            if rtn2 > 0:
                db.session.commit()
            else:
                command_id = data.get('command_id')
                logging.error(f'callAutorunFunc [command_id:{command_id}][msg:{msg}]')
                db.session.rollback()

        return jsonify({'return_code':1, 'message':'OK'}), 200

class AgentApi(BaseApi):

    resource_name = 'agent'

    @expose('/boot', methods=['POST'])
    @protect()
    def agentBoot(self, **kwargs):
        return jsonify({'return_code':1, 'message':'OK'}), 200

    @expose('/agent', methods=['POST'])
    @protect()
    def agent(self, **kwargs):

        data = json.loads(request.data)

        ip_address = request.remote_addr

        if not data.get('agent_id'):
            return jsonify({'return_code':-2,'message':'agent_id does not exist'}), 401
        elif not data.get('host_id'):
            return jsonify({'return_code':-2,'message':'host_id does not exist'}), 401
        elif not data.get('agent_type'):
            return jsonify({'return_code':-2,'message':'agent_type does not exist'}), 401

        agent_id   = data['agent_id']
        host_id    = data['host_id']
        agent_type = data['agent_type']
        installation_path  = data['installation_path']

        rtn , msg = addAgent(agent_id, host_id, agent_type, ip_address, installation_path=installation_path)
        
        return jsonify({'return_code':1, 'message':'OK'}), 200

    @expose('/download/<agent_type>/<file_name>', methods=['GET'])
    @protect()
    def download_file(self, agent_type, file_name):

        #get file name from db
        realname = getLatestFile(agent_type, file_name)

        if not realname:
            return jsonify({'return_code':-1, 'message':'File not found'}), 404

        fm = FileManager()
        fullname = fm.get_path(realname)

        return send_file(fullname, attachment_filename=file_name, as_attachment=True)
        
    @expose('/getRefreshToken/<agent_id>', methods=['GET'])
    @protect()
    def getRefreshToken(self, agent_id):

        refresh_token = create_refresh_token(g.user.id , expires_delta=timedelta(days=15))
        print('Hennry refresh token : ', refresh_token)
        expiration_date = datetime.now() + timedelta(days=15)
        rtn , msg = updateExpiration(agent_id, expiration_date, refresh_token)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg, 'refresh_token':''}), 401
        return jsonify({'return_code':rtn, 'message':'OK', 'refresh_token':refresh_token}), 200

class AjaxView(BaseView):

    route_base = '/ajax'
    default_view = 'ajax1'
	
    @expose('/ajax2', methods=['GET'])
    @has_access
    def ajax2(self):
        
        time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		
        return jsonify({'time':time})

    @expose('/ajax1', methods=['GET'])
    @has_access
    def ajax1(self):
        
        time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		
        return self.render_template("ajax1.html",name='hennry', time=time)

#appbuilder.add_view(AjaxView, "ajax test", category="ajax")
#appbuilder.add_link("ajax test", href="/ajax/ajax1", category="ajax")

appbuilder.add_view(
    AgentModelView,
    "Agent",
    icon="fa-folder-open-o",
    category="Agent&Command",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    AgentGroupModelView,
    "Agent 그룹",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_separator("Agent&Command")
appbuilder.add_view(
    FileModelView,
    "Files",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_separator("Agent&Command")
appbuilder.add_view(
    CommandTypeModelView,
    "Command 유형",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_view(
    CommandHelperModelView,
    "Command 규칙 관리",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_view(
    CommandMasterModelView,
    "Command 목록",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_view(
    CommandMasterAliveView,
    "활성 Command 목록",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_view(
    CommandDetailModelView,
    "Command 상세",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_view(
    AutorunResultModelView,
    "Command 처리결과 자동 반영 설정",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_view(
    ResultModelView,
    "Command 처리결과",
    icon="fa-folder-open-o",
    category="Agent&Command"
)
appbuilder.add_api(CommandApi)
appbuilder.add_api(AgentApi)