from flask import g, render_template, Flask, request, jsonify\
     , send_file, redirect, url_for, render_template_string, render_template
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import BaseView, ModelView, ModelRestApi, MultipleView, MasterDetailView
from flask_appbuilder import expose, has_access
from flask_appbuilder.widgets import ListWidget
from flask_appbuilder.actions import action
from flask_appbuilder.api import ModelRestApi, BaseApi, expose, safe, rison, protect
from flask_appbuilder.models.sqla.filters import get_field_setup_query, BaseFilter\
    , FilterEqualFunction, FilterNotEqual, FilterInFunction, FilterStartsWith, FilterEqual
from app import appbuilder, db, kafka_admin, WAS_STATUS
from flask_jwt_extended import create_refresh_token
#from .models import Server, JeusContainer, Host
from app.models.monitor import MoWasStatusTemplate, MoWasStatusReport, MoGridConfig, MoWasInstanceStatus
from .common import FilterStartsWithFunction, get_mw_user, get_userid, get_reporttime
from datetime import datetime, timedelta
from app.sqls.monitor import select_row, getGridConfig, createWasStatusReport\
                    , getNotRunningWasList, get_column_type, get_target_table_name\
                    , select_rows2
from app.sqls.agent import getAgentStat, getErrorResults, insertCommandMaster
from app.sqls.was import getChangedWAS, getChangedWEB
from wtforms import FieldList, StringField
from app.auto_report.runAutoReport import runAutoReport
import sys

class SimpleListWidget(ListWidget):
    template = 'widgets/list_hennry1.html'

class MoGridConfigModelView(ModelView):
    
    datamodel = SQLAInterface(MoGridConfig)
    
    list_title   = "Table 조회 화면 설정"
    list_columns = ['grid_key', 'title', 'table_name', 'columns'\
                    , 'headers', 'rows_per_page','page_dblclick', 'file_name']
    label_columns = {'grid_key'  :'API 파라메터'
                    ,'title'     :'화면 Title'
                    ,'table_name':'조회 Table명'
                    ,'columns'   :'조회 항목'
                    ,'headers'   :'조회 항목Title'
                    ,'widths'    :'칼럼 너비'
                    ,'seperator' :'list 구분자'
                    ,'default_condition' :'기본조건'
                    ,'condition_columns' :'조회조건항목'
                    ,'condition_labels' :'조회조건LABEL'
                    ,'page_dblclick' : '더블클릭시 Open할 Page'
                    ,'rows_per_page' : 'Page당 조회 건수'
                    ,'file_name' :'Export파일명'
                    }

    description_columns = {
         'default_condition':'입력 예 : {"column":"mw_was.was_id","operator":"eql","value":"DETC_Domain"},{...}'
        ,'condition_labels':'조회조건항목에 1:1로 순서에 맞춰 입력'
        ,'headers':'조회 항목에 1:1로 순서에 맞춰 입력'
    }
    edit_exclude_columns = ['update_on', 'create_on']
    add_exclude_columns = ['update_on', 'create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class MoWasInstanceStatusModelView(ModelView):
    
    datamodel = SQLAInterface(MoWasInstanceStatus)

    list_title   = "WAS instance 상태"    
    list_columns = ['was_id', 'was_instance_id', 'was_instance_status', 'host_id'\
                    , 'landscape','update_on']
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class MoWasStatusTemplateModelView(ModelView):
    
    datamodel = SQLAInterface(MoWasStatusTemplate)
    
    list_title   = "WAS일일점검 Template"
    list_columns = ['was_id', 'was_instance_group', 'wi_01', 'wi_02', 'wi_03', 'wi_04', 'wi_05'\
                    , 'wi_06', 'wi_07', 'wi_08', 'wi_09', 'wi_10'\
                    , 'wi_11', 'wi_12', 'wi_13', 'wi_14', 'wi_15'\
                    , 'wi_16', 'wi_17', 'wi_18', 'wi_19', 'wi_20'\
                    , 'wi_21', 'wi_22', 'wi_23', 'wi_24', 'wi_25']
    label_columns = {'was_id':'WAS'
                    ,'was_instance_group':'was instance 그룹'}

    edit_exclude_columns = ['update_on', 'create_on']
    add_exclude_columns = ['update_on', 'create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class MoWasStatusReportModelView(ModelView):
    
    datamodel = SQLAInterface(MoWasStatusReport)

    list_widget  = SimpleListWidget
    list_template = 'listNoOption.html'

    page_size = 200

    list_title   = 'WAS 상태 Report'
    list_columns = ['was_id', 'was_instance_group'\
                    , 'c_wi_01', 'c_wi_02', 'c_wi_03', 'c_wi_04', 'c_wi_05'\
                    , 'c_wi_06', 'c_wi_07', 'c_wi_08', 'c_wi_09', 'c_wi_10'\
                    , 'c_wi_11', 'c_wi_12', 'c_wi_13', 'c_wi_14', 'c_wi_15'\
                    , 'c_comment', 'reported_time'
                    , 'checked_date']
    label_columns = {'was_id':'WAS'
                    ,'was_instance_group':'서버'
                    , 'c_wi_01':' ', 'c_wi_02':' ', 'c_wi_03':' ', 'c_wi_04':' ', 'c_wi_05':' '
                    , 'c_wi_06':' ', 'c_wi_07':' ', 'c_wi_08':' ', 'c_wi_09':' ', 'c_wi_10':' '
                    , 'c_wi_11':' ', 'c_wi_12':' ', 'c_wi_13':' ', 'c_wi_14':' ', 'c_wi_15':' '
                    , 'c_comment':'비고'
                    , 'checked_date':'확인일시' }
    formatters_columns={'checked_date': lambda x:x.strftime('%Y.%m.%d %H:%M')}
    base_filters = [['reported_time', FilterStartsWithFunction, get_reporttime]
                    ]

    base_order = ('was_instance_group', 'asc')    

    @action("create_report","create report","진짜로?","fa-rocket",single=False)
    def create_report(self, items):

        print('Here')
        rtn , msg = createWasStatusReport()

        self.update_redirect()
        return redirect(self.get_redirect())

class MonitorApi(BaseApi):

    route_base = '/monitor'

    condtype_map ={
        'enum':['eql','neql']
       ,'str':['eql','neql','like','nlike']
       ,'int':['eql','neql','gt','lt']
       ,'datetime':['eql','neql','gt','lt']
       ,'tag':['and','or']
    }

    """
    @expose('/createWasStatusReport', methods=['PUT'])
    @protect()
    def createWasStatusReport(self):

        rtn , msg = createWasStatusReport()
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 401
        return jsonify({'return_code':rtn, 'message':'OK'}), 200
    """

    @expose('/test', methods=['GET'])
    @expose('/test/<param>', methods=['GET'])
    @has_access
    def test(self, param=None):

        cond_list = []
        if param:
            param = str(param)
            rec = getGridConfig(param)

            table_name = rec.table_name
            conditions = rec.condition_columns.split(',') if rec.condition_columns else ''
            cond_labels = rec.condition_labels.split(',') if rec.condition_labels else conditions

            for c, label in zip(conditions, cond_labels):
                
                if '.' in c:
                    val = c.split('.')
                    target_table_name = get_target_table_name(table_name, val[0])
                    cond_list.append(dict(
                        name = c
                       ,label = label
                       ,type = get_column_type(target_table_name, val[1])
                       ,operations=self.condtype_map[get_column_type(target_table_name, val[1])])
                    )
                else:
                    cond_list.append(dict(
                        name = c
                       ,label = label
                       ,type = get_column_type(table_name, c)
                       ,operations=self.condtype_map[get_column_type(table_name, c)])
                    )

        else:
            param = ''

        return render_template('list_jqgrid.html'\
            , param=param
            , condition=cond_list
            , url='/monitor/test'
            , base_template=appbuilder.base_template
            , appbuilder=appbuilder
            )

    @expose('/viewTableSpecs', methods=['GET'])
    @has_access
    def viewTableSpecs(self):

        grid_header = [
        {'name':'name', 'label':'Column 이름', 'width':200},
        {'name':'type', 'label':'Column Type', 'width':130},
        {'name':'comment', 'label':'Comment', 'width':250},
        {'name':'foreign', 'label':'Foreign Key', 'width':250}
        ]
        return render_template('list_jqgrid_tablespec.html'\
            , grid_header=grid_header
            , tables='/api/v1/model/tables'\
            , modelinfo='/api/v1/model/modelinfo'\
            , base_template=appbuilder.base_template, appbuilder=appbuilder)

    @expose('/jobSchedulerList', methods=['GET'])
    @has_access
    def jobSchedulerList(self):

        return render_template('show_jsonviewer.html', url='/scheduler/jobs'\
            , title='정기 JOB 목록'
            , base_template=appbuilder.base_template, appbuilder=appbuilder)
    
    @expose('/agentOffsetList', methods=['GET'])
    @has_access
    def agentOffsetList(self):

        return render_template('show_jsonviewer.html', url='/monitor/agentOffsets'\
            , title='Agent Health Check'
            , base_template=appbuilder.base_template, appbuilder=appbuilder)

    @expose('/getAccessToken', methods=['GET'])
    @has_access
    def getAccessToken(self):

        row, _ = select_row('ab_user',{'username':'agent'})
        data = create_access_token(identity=row.id)
        return render_template('show_raw.html', title='agent access token', html=data
                , copy=True
                , base_template=appbuilder.base_template, appbuilder=appbuilder)

    @expose('/getRefleshToken', methods=['GET'])
    @has_access
    def getRefleshToken(self):

        row, _ = select_row('ab_user',{'username':'agent'})
        data = create_refresh_token(identity=row.id, expires_delta=timedelta(hours=1))
        return render_template('show_raw.html', title='agent reflesh token (short-term)', html=data
                , copy=True
                , base_template=appbuilder.base_template, appbuilder=appbuilder)

    @expose('/agentOffsets', methods=['GET'])
    @has_access
    def agentOffsets(self):

        if kafka_admin:
            result, _ = kafka_admin.getOffSets(topic='t_agent_health', partition=0)
        else:
            result = []
        return jsonify(result)


    @expose('/getWasStatus', methods=['GET'])
    @has_access
    def getWasStatus(self):

        return jsonify({'data':WAS_STATUS,'checked_date':datetime.now().strftime("%Y/%m/%d %H:%M:%S")})

    
    @expose('/getWasStatusList', methods=['GET'])
    @has_access
    def getWasStatusList(self):

        return render_template('show_gridly.html', url='/monitor/getWasStatus'\
        #return render_template('show_jsonviewer.html', url='/monitor/getWasStatus'\
            , title='WAS Status Check'
            , base_template=appbuilder.base_template, appbuilder=appbuilder)

    @expose('/recheckStatus', methods=['GET'])
    @has_access
    def recheckStatus(self):

        message = '비정상인 WAS가 존재하지 않습니다.'
        trace = ''

        _, _, was_l = getNotRunningWasList()

        command_type_id = ''
        agent_id = ''
        agents = []

        if was_l:

            try:
                # w is a tuple (was_id, agent_id)
                for w in was_l:
                    if w[0] in ['PKIF_Domain','PWMM_Domain']:
                        command_type_id = 'NOAGENT.JMX.MONITOR'
                        agent_id = 'ESX05_syper_J'
                    else:
                        rec, _ = select_row('ag_command_helper', dict(mapping_key='ASIS_JMX_PARAMS',agent_id=w[1]))
                        if rec:
                            command_type_id = 'ASIS.P.JMX.MONITOR'
                        else:
                            command_type_id = 'NEWGEN.jmx.monitor'
                        agent_id = w[1]

                    insertCommandMaster(command_type_id, [agent_id])

                    agents.append(agent_id)

                db.session.commit()
            
                message = ','.join(agents) + ' 에 WAS상태 정보를 요청하였습니다.'

            except Exception as e:
                excType, excValue, traceback_ = sys.exc_info()
                print(e.with_traceback(traceback_))
                message = 'WAS상태Update가 실패하였습니다.'
                trace = str(e.with_traceback(traceback_))

        return jsonify({'message':message, 'trace':trace})

    @expose('/sendDailyReport', methods=['GET'])
    @expose('/sendDailyReport/<was_check>', methods=['GET'])
    @has_access
    def sendDailyReport(self, was_check=None):

        message = '일일보고 발송이 성공하였습니다.'
        trace = ''

        try:

            print('HH :',g.user.username, g.user.email)
            sender      = g.user.email
            sender_name = g.user.first_name
            receivers   = ['o2000988@gwe.kdb.co.kr','o2000990@gwe.kdb.co.kr','o2000866@gwe.kdb.co.kr','o1404902@gwe.kdb.co.kr']
            ccs         = ['o2000866@gwe.kdb.co.kr']

            if was_check=='0':
                print("HHH 0")
                is_was_check = False
            else:
                is_was_check = True

            runAutoReport(sender, sender_name, receivers, ccs, was_check=is_was_check)
        except Exception as e:
            excType, excValue, traceback_ = sys.exc_info()
            print(e.with_traceback(traceback_))
            message = '일일보고 발송이 실패하였습니다.'
            trace = str(e.with_traceback(traceback_))

        return jsonify({'message':message, 'trace':trace})

    @expose('/getNotRunningWasList', methods=['GET'])
    @has_access
    def getNotRunningWasList(self):

        uncheckedWas_list, notRunningWas_list, _ = getNotRunningWasList()

        return jsonify({'uncheckedWas':uncheckedWas_list,'notRunningWas':notRunningWas_list})

    @expose('/agentStat', methods=['GET'])
    @has_access
    def agentStat(self):

        agentStat_recs, offline_recs = getAgentStat()

        agentStat_list = []
        if agentStat_recs:
            [ agentStat_list.append({'landscape':'NON' if r.landscape==None\
                 else r.landscape.name,'total':r.total, 'offline':r.offline})\
             for r in agentStat_recs ]

        offline_list = []
        if offline_recs:
            [ offline_list.append(
                {'landscape':'NON' if r.landscape==None else r.landscape.name
                ,'agent_id':r.agent_id
                ,'agent_name':r.agent_name
                , 'last_checked_date':r.last_checked_date.strftime('%Y.%m.%d %H:%M')}
                ) for r in offline_recs ]

        return jsonify({'agentStat':agentStat_list, 'offlineAgents':offline_list})

    @expose('/getErrorResults', methods=['GET'])
    @has_access
    def getErrorResults(self):

        d3daysAgo = datetime.now() - timedelta(days=3)
        recs = getErrorResults(create_on=d3daysAgo)

        configFiles_List = []
        erroWas_List = []

        if recs:
            for r in recs:
                
                if r.key_value1 == 'get_server_stat':

                    if any( r.command_id == l['command_id'] and r.host_id == l['host_id'] and r.key_value2 == l['key_value2'] for l in erroWas_List):
                        continue

                    erroWas_List.append(
                        {'id':r.id
                        ,'command_id':r.command_id
                        ,'host_id':r.host_id
                        ,'agent_id':r.ag_command_detail.agent_id
                        ,'key_value2':r.key_value2
                        ,'result_status':r.result_status.value
                        ,'result_text':r.result_text
                        ,'create_on':r.create_on.strftime('%Y.%m.%d %H:%M')}
                    )
                elif r.ag_command_detail.command_class.name == 'ReadPlainFile':

                    configFiles_List.append(
                        {'id':r.id
                        ,'command_id':r.command_id
                        ,'host_id':r.host_id
                        ,'agent_id':r.ag_command_detail.agent_id
                        ,'key_value1':r.key_value1
                        ,'key_value2':r.key_value2
                        ,'result_status':r.result_status.value
                        ,'create_on':r.create_on.strftime('%Y.%m.%d %H:%M')}
                    )

        return jsonify({'configFilesList':configFiles_List,'erroWasList':erroWas_List})

    @expose('/recent_knowledge_list', methods=['GET'])
    @has_access
    def recent_knowledge_list(self):

        d3daysAgo = datetime.now() - timedelta(days=3)

        recent_knowledge_list = []
        condition = [dict(column='update_on', operator='gt', value=d3daysAgo)]
        sort_condition = [dict(column='update_on', option='desc')]
        
        recs, _ = select_rows2('ut_html_content', condition=condition, sort_condition=sort_condition)
        
        if recs:
            [ recent_knowledge_list.append(
                {'id':r.id
                ,'content_name':r.content_name
                ,'user_id':r.user_id
                ,'category':next(( t.label for t in r.ut_tag if t.tag.startswith('지식유형-')),'')
                ,'update_on':r.update_on.strftime('%Y.%m.%d %H:%M')
                ,'create_on':r.create_on.strftime('%Y.%m.%d %H:%M')}
                ) for r in recs ]

        return jsonify({'recent_knowledge_list':recent_knowledge_list})


    @expose('/get_changed_configs', methods=['GET'])
    @has_access
    def get_changed_configs(self):

        d3daysAgo = datetime.now() - timedelta(days=3)

        changedWAS_List = []
        recs = getChangedWAS(create_on=d3daysAgo)
        if recs:
            [ changedWAS_List.append(
                {'id':r.id
                ,'landscape':'NON' if r.mw_was.landscape==None else r.mw_was.landscape.name
                ,'was_id':r.mw_was.was_id
                ,'was_name':r.mw_was.was_name
                ,'host_id':r.mw_was.located_host_id
                ,'create_on':r.create_on.strftime('%Y.%m.%d %H:%M')}
                ) for r in recs ]

        changedWEB_List = []
        recs = getChangedWEB(create_on=d3daysAgo)
        if recs:
            [ changedWEB_List.append(
                {'id':r.id
                ,'landscape':'NON' if r.mw_web.landscape==None else r.mw_web.landscape.name
                ,'port':r.mw_web.port
                ,'host_id':r.mw_web.host_id
                ,'web_name':r.mw_web.web_name
                ,'create_on':r.create_on.strftime('%Y.%m.%d %H:%M')}
                ) for r in recs ]

        return jsonify({'changedWASList':changedWAS_List,'changedWEBList':changedWEB_List})

appbuilder.add_view(
    MoWasStatusTemplateModelView,
    "WAS 상태 Template",
    icon="fa-folder-open-o",
    category="Monitor",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    MoWasInstanceStatusModelView,
    "WAS 상태 조회",
    icon="fa-folder-open-o",
    category="Monitor",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    MoWasStatusReportModelView,
    "WAS 상태 Report",
    icon="fa-folder-open-o",
    category="Monitor",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    MoGridConfigModelView,
    "Table 목록 조회 설정",
    icon="fa-folder-open-o",
    category="Monitor",
    category_icon="fa-envelope"
)
appbuilder.add_link(
    name='TABLE.INFO',
    href='/monitor/test',
    label="Table 정보 조회",
    icon="fa-envelope",
    category="Monitor"
)
appbuilder.add_link(
    name='JOB.LIST',
    href='/monitor/jobSchedulerList',
    label="JOB Schedule List",
    icon="fa-envelope",
    category="System"
)
appbuilder.add_link(
    name='AGENTOFFSET.LIST',
    href='/monitor/agentOffsetList',
    label="Agent Health List",
    icon="fa-envelope",
    category="System"
)
appbuilder.add_link(
    name='WASSTATUS.LIST',
    href='/monitor/getWasStatusList',
    label="WAS Status List",
    icon="fa-envelope",
    category="System"
)
appbuilder.add_link(
    name='viewTableSpecs',
    href='/monitor/viewTableSpecs',
    label="Table 상세 조회",
    icon="fa-envelope",
    category="System"
)
appbuilder.add_link(
    name='getRefleshToken',
    href='/monitor/getRefleshToken',
    label="Agent용 Token 발급",
    icon="fa-envelope",
    category="System"
)
appbuilder.add_api(MonitorApi)
