from flask import g, render_template, Flask, request, jsonify\
     , send_file, redirect, url_for, render_template_string
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import BaseView, ModelView, ModelRestApi, MultipleView, MasterDetailView
from flask_appbuilder import expose, has_access
from flask_appbuilder.actions import action
from flask_appbuilder.api import ModelRestApi, BaseApi, expose, safe, rison, protect
from flask_appbuilder.models.sqla.filters import get_field_setup_query, BaseFilter\
    , FilterEqualFunction, FilterNotEqual, FilterInFunction, FilterStartsWith, FilterEqual
from app import appbuilder, db #, mongoClient, dbMongo, footprint, vv_P_secs
#from .models import Server, JeusContainer, Host
from app.models.was import MwServer, MwWas, MwWasInstance, MwWeb, MwWebVhost, MwWasHttpListener\
    , MwWasWebtobConnector, MwWebReverseproxy, MwDatasource, MwApplication, DailyReport\
    , MwWebServer, MwWebUri, MwWaschangeHistory, MwWebchangeHistory\
    , MwBizCategory, MwAppMaster, MwDBMaster, MwWebDomain, MwWebSsl
from app.models.knowledge import UtTag
from app.sqls.was import getWasInstanceId, getLandscape\
    , getWasRelationship, getWebRelationship
from app.sqls.agent import createConnectSSL, createFileSSL, insertCommandMaster, getAgent
from app.sqls.batch import createDomainNameInfo, createSslInfo
from app.sqls.monitor import select_row, selectItem, selectItems
from app.dmlsForAgent import AutorunResult
from app.dmlsForJeus import JeusDomain, JeusDomainFactory, OldJeusDomain, NewJeusDomain
from .common import FilterStartsWithFunction, get_mw_user, get_userid, ShowWithIds, ListAdvanced

import json
import xmltodict
from deepdiff import DeepDiff
# Excel
import pandas as pd
from io import BytesIO
import xlsxwriter

# Chart
#import io
#import plotly.express as px

class DatasourceModelView(ModelView):
    
    datamodel = SQLAInterface(MwDatasource)
    
    list_title   = "WAS Datasource 목록"    
    list_columns = ['was_id', 'was_name', 'datasource_id', 'db_jndi_id', 'vender_name'\
                   , 'db_user_id', 'db_dbms_id', 'db_pool_min', 'db_pool_max', 'db_server_name', 'datasource_class_name']
    label_columns = {'was_id':'WAS'
                    ,'was_name':'WAS 명'
                    ,'datasource_id':'DataSource Id'
                    ,'db_jndi_id':'Export(JNDI) 이름'
                    ,'db_property':'DB 접속정보'
                    ,'vender_name':'JDBC Vendor'
                    ,'db_server_name':'DB 서버'
                    ,'db_dbms_id':'DB 명'
                    ,'datasource_class_name':'JDBC Class'
                    ,'db_user_id':'DB User'
                    ,'db_pool_min':'DB Pool Min'
                    ,'db_pool_max':'DB Pool Max'
                    ,'db_pool_step':'DB Pool Step'
                    ,'db_pool_period':'DB Pool Perid'}

    search_columns = ['mw_was', 'db_user_id', 'db_dbms_id', 'db_server_name']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WaschangeHistoryModelView(ModelView):
    
    datamodel = SQLAInterface(MwWaschangeHistory)
    show_template = 'showWithJson.html'
    show_widget  = ShowWithIds
    
    extra_args = {'buttonList':[
            {'text':'WAS 속성 변경내역','id':'json-button','onclick':'renderJson("Changed Object","WAS 속성 변경내역")'}
          , {'text':'WAS 변경 전 내역','id':'json-button','onclick':'renderJson("Old Was Object","WAS 변경 전 내역")'}
        ]}

    list_title   = "WAS Config 변경 이력"    
    list_columns = ['mw_was.was_id', 'create_on']
    label_columns = {'mw_was.was_id':'WAS'
                    ,'create_on':'변경일시'}

    search_columns = ['mw_was','create_on']
    base_order = ('create_on', 'desc')
    base_permissions = ['can_list', 'can_show']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class ApplicationModelView(ModelView):
    
    datamodel = SQLAInterface(MwApplication)

    list_title   = "WAS Application 목록"    
    list_columns = ['was_id', 'application_id', 'application_home', 'context_path'\
                    ,'filtered_text', 'deploy_type']
    label_columns = {'was_id':'WAS'
                    ,'application_id':'Application ID'
                    ,'application_home':'Application 배포 위치'
                    ,'context_path':'Context Path'
                    ,'filtered_text':'색출정보'
                    ,'deploy_type':'배포Type'}

    search_columns = ['mw_was']
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WasHttpListenerModelView(ModelView):

    datamodel = SQLAInterface(MwWasHttpListener)

    list_title   = "WAS Http Listener 목록"    
    list_columns = ['was_id', 'was_instance_id', 'host_id', 'webconnection_id', 'listen_port'\
                    ,'min_thread_pool_count', 'max_thread_pool_count']
    label_columns = {'was_id':'WAS Domain'
                    ,'was_instance_id':'MS intance id'
                    ,'host_id':'HOST ID'
                    ,'webconnection_id':'Web Connection ID'
                    ,'listen_port':'서비스Port'
                    ,'min_thread_pool_count':'Min Thread pool 개수'
                    ,'max_thread_pool_count':'Max Thread pool 개수'}

    search_columns = ['was_id', 'mw_was_instance', 'webconnection_id']

    edit_exclude_columns = ['httplistener_object','create_on']
    add_exclude_columns = ['httplistener_object','create_on']
    search_exclude_columns = ['httplistener_object']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WasWebtobConnectorModelView(ModelView):

    datamodel = SQLAInterface(MwWasWebtobConnector)

    list_title   = "WAS Webtob Connector 목록"    
    list_columns = ['was_id', 'was_instance_id', 'host_id', 'webconnection_id', 'web_host_id'\
                    ,'jsv_port', 'jsv_id', 'thread_pool_count', 'disable_pipe','web_home']
    label_columns = {'was_id':'WAS Domain'
                    ,'was_instance_id':'MS intance id'
                    ,'host_id':'HOST ID'
                    ,'webconnection_id':'Web Connection ID'
                    ,'web_host_id':'Web서버 host id'
                    ,'jsv_port':'Web서버 JSV Port'
                    ,'jsv_id':'JSV ID'
                    ,'web_home':'webtob home'
                    ,'thread_pool_count':'JSV Session 개수'}

    search_columns = ['was_id', 'mw_was_instance', 'web_host_id']

    edit_exclude_columns = ['webtobconnector_object','create_on']
    add_exclude_columns = ['webtobconnector_object','create_on']
    search_exclude_columns = ['webtobconnector_object']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WasInstanceModelView(ModelView):

    datamodel = SQLAInterface(MwWasInstance)

    list_title   = "WAS Instance 목록"    
    list_columns = ['was_id', 'was_instance_id', 'landscape', 'newgeneration_yn', 'was_instance_port'\
                    , 'host_id', 'c_os_type', 'c_ip_address','min_heap_size', 'max_heap_size', 'clustered_yn'\
                    , 'colored_apm_type', 'use_yn', 'mw_datasource', 'mw_application']
    label_columns = {'was_id':'WAS Domain'
                    ,'was_instance_id':'MS intance id'
                    ,'was_instance_port':'Port'
                    ,'host_id':'설치 장비'
                    ,'c_os_type':'OS'
                    ,'newgeneration_yn':'차세대'
                    ,'c_ip_address':'IP'
                    ,'min_heap_size':'Min Heep Size(M)'
                    ,'max_heap_size':'Max Heep Size(M)'
                    ,'clustered_yn':'Clustering'
                    ,'apm_type':'APM'
                    ,'use_yn':'사용구분'
                    ,'colored_apm_type':'APM'
                    ,'mw_datasource':'Data Source'
                    ,'mw_application':'Application'}

    edit_exclude_columns = ['create_on']
    base_order = ('was_instance_id', 'asc')
    search_columns = ['was_id', 'was_instance_id', 'host_id', 'apm_type'\
                    ,'min_heap_size', 'max_heap_size', 'clustered_yn']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]
    related_views = [WasWebtobConnectorModelView, WasHttpListenerModelView]

class WasModelView(ModelView):
    
    datamodel = SQLAInterface(MwWas)

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    extra_args = {
        'buttonList':[
         {'text':'운영','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_landscape=PROD'}
        ,{'text':'개발','id':'toggle_bt2','bt_group':'1','onclick':'_flt_0_landscape=DEV'}
        ,{'text':'이관','id':'toggle_bt3','bt_group':'1','onclick':'_flt_0_landscape=TEST'}
        ,{'text':'차세대','id':'toggle_bt3','bt_group':'2','onclick':'_flt_0_newgeneration_yn=YES'}
        ,{'text':'유지','id':'toggle_bt4','bt_group':'2','onclick':'_flt_0_newgeneration_yn=NO'}
        ],
        'selectList':[
         {'text':'Hostname','id':'host-selector','combind':'0','type':'parent'}
        ,{'text':'시스템','id':'tag-selector','combind':'0','type':'parent','condition':{'operator':'and','column':'tag','value':'시스템'}}
        ],
        'inputList':[
         {'text':'WAS 이름','id':'was-name','combind':'0','condition':'_flt_2_was_name=','size':20}
        ]
        }

    list_title   = "JEUS 목록"    
    list_columns = ['c_was_id', 'newgeneration_yn', 'was_name', 'colored_landscape'\
                    , 'system_user', 'located_host_id', 'c_os_type', 'link_ip_address', 'running_type', 'standby_host_id'\
                    , 'view_domaininfo','view_relationship']
    label_columns = {'c_was_id':'WAS Domain'
                    ,'was_name':'WAS 이름'
                    ,'newgeneration_yn':'차세대'
                    ,'adminserver_name':'AdminServer 이름'
                    ,'landscape':'Landscape'
                    ,'colored_landscape':'Landscape'
                    ,'t__it_incharge':'담당자'
                    ,'system_user':'서버계정'
                    ,'running_type':'이중화'
                    ,'standby_host_id':'StandBy'
                    ,'located_host_id':'설치 node'
                    ,'c_os_type':'OS'
                    ,'link_ip_address':'IP'
                    ,'view_domaininfo':'Config'
                    ,'view_relationship':'관계도'}

    edit_exclude_columns = ['cluster_object','was_object','license_update_date','jeus_properties_update_date','create_on']
    add_exclude_columns = ['cluster_object','was_object','license_update_date','jeus_properties_update_date','create_on']
    search_exclude_columns = ['cluster_object','was_object']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]
                    ,['use_yn', FilterEqual, 'YES']]
    base_order = ('c_was_id', 'asc')    

    related_views = [WasInstanceModelView, ApplicationModelView, DatasourceModelView, WaschangeHistoryModelView]

    @action("call_filtered_info","Update Findings in App","","fa-rocket",single=False)
    def callFilteredInfo(self, items):

        for item in items:

            agent_rec = getAgent(item.agent_id)

            if not agent_rec:
                continue

            recs, _ = selectItems('mw_application', 'application_home', dict(was_id=item.was_id))

            for rec in recs:

                addparam = item.was_id

                if rec.application_home.endswith(".war"):
                    addparam += ' ' + rec.application_home
                elif rec.application_home.endswith(".jar"):
                    continue
                else:
                    addparam += ' ' + rec.application_home

                #JEUS7, JEUS8 인 경우 ExeScript 실행
                if item.mw_server.os_type.name == 'WINDOWS':
                    addparam += ' ' + '^.*log4.*.jar'
                    insertCommandMaster('EXE.FILTER4WIN', [agent_rec.agent_id], addparam)
                #elif item.mw_server.os_type.name == 'HPUX' and item.newgeneration_yn.name == 'NO':
                elif item.mw_server.os_type.name == 'HPUX':
                    addparam += ' ' + '*log4*.jar'
                    insertCommandMaster('RUN.FILTER', [agent_rec.agent_id], addparam, out_CID=True)
                else:
                    filter_dict = dict(was_id=item.was_id
                                    , application_home=rec.application_home)
                    appRec, _ = \
                            selectItem('mw_application', 'application_id', filter_dict)
                    addparam += ' ' + '*log4*.jar' + ' ' + appRec.application_id
                    insertCommandMaster('EXE.FILTER', [agent_rec.agent_id], addparam)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class WasLinkView(ModelView):
    
    datamodel = SQLAInterface(MwWas)

    list_title   = "JEUS 목록(차세대-운영)"    
    list_columns = ['was_id', 'was_name', 'link_ip_address', 'located_host_id', 'newgeneration_yn', 'colored_landscape'\
                    , 't__it_incharge']
    label_columns = {'was_id':'WAS Domain'
                    ,'was_name':'WAS 이름'
                    ,'newgeneration_yn':'차세대'
                    ,'adminserver_name':'AdminServer 이름'
                    ,'landscape':'운영/이관/개발/DR'
                    ,'colored_landscape':'운영/이관/개발/DR'
                    ,'t__it_incharge':'담당자'
                    ,'located_host_id':'설치 node'
                    ,'link_ip_address':'WebAdmin Link'}

    search_exclude_columns = ['cluster_object','was_object']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]
                    ,['landscape', FilterEqual, 'PROD']
                    ,['newgeneration_yn', FilterEqual, 'YES']
                    ]
    base_order = ('was_id', 'asc')    
    base_permissions = ['can_list']
    
    related_views = [WasInstanceModelView, ApplicationModelView, DatasourceModelView]

class WasLicenseView(ModelView):
    
    datamodel = SQLAInterface(MwWas)

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    extra_args = {
        'buttonList':[
         {'text':'운영','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_landscape=PROD'}
        ,{'text':'개발','id':'toggle_bt2','bt_group':'1','onclick':'_flt_0_landscape=DEV'}
        ,{'text':'이관','id':'toggle_bt3','bt_group':'1','onclick':'_flt_0_landscape=TEST'}
        ,{'text':'차세대','id':'toggle_bt3','bt_group':'2','onclick':'_flt_0_newgeneration_yn=YES'}
        ,{'text':'유지','id':'toggle_bt4','bt_group':'2','onclick':'_flt_0_newgeneration_yn=NO'}
        ],
        'selectList':[
         {'text':'Hostname','id':'host-selector','combind':'0','type':'parent'}
        ],
        'inputList':[
         {'text':'WAS 이름','id':'was-name','combind':'0','condition':'_flt_2_was_name=','size':20}
        ]
        }

    list_title   = "JEUS License 정보"    
    list_columns = ['c_was_id', 'was_name', 'link_ip_address', 'located_host_id'\
                    , 'newgeneration_yn', 'colored_landscape', 'use_yn'\
                    , 'license_update_date', 'license_cpu', 'license_edition', 'version_info'\
                    , 'license_hostname', 'license_issue_date', 'license_due_date'
                    ]
    label_columns = {'c_was_id':'WAS Domain'
                    ,'was_name':'WAS 이름'
                    ,'newgeneration_yn':'차세대'
                    ,'adminserver_name':'AdminServer 이름'
                    ,'landscape':'운영/이관/개발/DR'
                    ,'colored_landscape':'운영/이관/개발'
                    ,'use_yn':'사용여부'
                    ,'license_update_date':'license 확인'
                    ,'license_cpu':'CPU수량'
                    ,'license_edition':'Edition'
                    ,'version_info':'WAS 버젼'
                    ,'license_hostname':'license서버'
                    ,'license_issue_date':'license발급일'
                    ,'license_due_date':'license만료일'
                    ,'located_host_id':'WAS node'
                    ,'link_ip_address':'IP Address'}
    show_columns = ['license_text']
    search_exclude_columns = ['cluster_object','was_object']

    formatters_columns={'license_update_date': lambda x:x.strftime('%Y-%m-%d %H:%M') if x else ''
                        ,'license_issue_date': lambda x:x.strftime('%Y-%m-%d') if x else ''
                        ,'license_due_date': lambda x:x.strftime('%Y-%m-%d') if x else ''}

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]
    base_order = ('was_id', 'asc')    
    base_permissions = ['can_list','can_show']

    @action("call_file_jeus_license","Update Jeus License","","fa-rocket",single=False)
    def callFileJeusLicense(self, items):

        for item in items:

            if item.mw_server.os_type.name == 'WINDOWS':
                agent_id = item.located_host_id.upper() + '_' + item.system_user + '_J'
            else:
                agent_id = item.located_host_id + '_' + item.system_user + '_J'

            agent_rec = getAgent(agent_id)

            if not agent_rec:
                continue

            addparam = item.was_id

            filter_dict = dict(mapping_key='DOMAIN_HOME'
                            , target_file_name=item.was_id
                            , agent_id=agent_id)
            rec, _ = select_row('ag_command_helper', filter_dict)

            if rec:
                addparam += ' ' + rec.string_to_replace
            else:
                addparam += ' /sw/jeus/bin/'

            #JEUS7, JEUS8 인 경우 ExeScript 실행
            if item.mw_server.os_type.name == 'WINDOWS':
                insertCommandMaster('EXE.JEUS.LICENSE4WIN', [agent_rec.agent_id], addparam)
            elif item.mw_server.os_type.name == 'HPUX':
                insertCommandMaster('RUN.JEUS.LICENSE', [agent_rec.agent_id], addparam, out_CID=True)
            else:
                insertCommandMaster('EXE.JEUS.LICENSE', [agent_rec.agent_id], addparam)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class WebLicenseView(ModelView):
    
    datamodel = SQLAInterface(MwWeb)

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    extra_args = {
        'buttonList':[
         {'text':'운영-차세대','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_newgeneration_yn=YES&_flt_0_landscape=PROD'}
        ,{'text':'운영-유지','id':'toggle_bt2','bt_group':'1','onclick':'_flt_0_newgeneration_yn=NO&_flt_0_landscape=PROD'}
        ,{'text':'개발-차세대','id':'toggle_bt3','bt_group':'1','onclick':'_flt_0_newgeneration_yn=YES&_flt_0_landscape=DEV'}
        ,{'text':'개발-유지','id':'toggle_bt4','bt_group':'1','onclick':'_flt_0_newgeneration_yn=NO&_flt_0_landscape=DEV'}
        ,{'text':'이관-차세대','id':'toggle_bt5','bt_group':'1','onclick':'_flt_0_newgeneration_yn=YES&_flt_0_landscape=TEST'}
        ,{'text':'이관-유지','id':'toggle_bt6','bt_group':'1','onclick':'_flt_0_newgeneration_yn=NO&_flt_0_landscape=TEST'}
        ],
        'selectList':[
         {'text':'Hostname','id':'host-selector','combind':'0','type':'parent'}
        ],
        'inputList':[
         {'text':'WEB 이름','id':'web-name','combind':'0','condition':'_flt_2_web_name=','size':20}
        ]
        }

    list_title   = "WEBTOB License 정보"    
    list_columns = ['c_host_id', 'c_ip_address', 'port', 'colored_landscape','newgeneration_yn'\
                    , 'web_name','port', 'colored_built_type', 'use_yn'\
                    , 'license_update_date', 'license_cpu', 'license_edition'\
                    , 'license_hostname', 'license_issue_date', 'license_due_date'
                    ]
    label_columns = {'c_host_id':'Host ID'
                    ,'port':'Port'
                    ,'newgeneration_yn':'차세대여부'
                    ,'colored_landscape':'Landscape'
                    ,'web_name':'설명'
                    ,'port':'Port'
                    ,'doc_dir':'DOC root'
                    ,'c_ip_address':'IP'
                    ,'colored_built_type':'내장/외장'
                    ,'use_yn':'사용여부'
                    ,'license_update_date':'license 확인'
                    ,'license_cpu':'CPU수량'
                    ,'license_edition':'Edition'
                    ,'license_hostname':'license서버'
                    ,'license_issue_date':'license발급일'
                    ,'license_due_date':'license만료일'
                    ,'located_host_id':'WAS node'
                    ,'link_ip_address':'IP Address'}

    show_columns = ['license_text']
    search_exclude_columns = ['ssl_object','proxy_ssl_object','logging_object','errordocument_object'\
                            , 'ext_object', 'tcpgw_object', 'httpm_object']

    formatters_columns={'license_update_date': lambda x:x.strftime('%Y-%m-%d %H:%M') if x else ''
                        ,'license_issue_date': lambda x:x.strftime('%Y-%m-%d') if x else ''
                        ,'license_due_date': lambda x:x.strftime('%Y-%m-%d') if x else ''}

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]
    base_order = ('host_id', 'asc')    
    base_permissions = ['can_list','can_show']

    @action("call_file_webtob_license","Update Webtob License","","fa-rocket",single=False)
    def callFileWebtobLicense(self, items):

        for item in items:

            agent_rec = getAgent(item.agent_id)

            if not agent_rec:
                continue

            addparam = item.host_id + '__' + str(item.port) + ' ' + item.web_home + '/bin/' + ' ' + item.web_home + '/license/license.dat'

            #HPUX 인 경우 ExeScript 의 stdout을 못가져옴
            if item.mw_server.os_type.name == 'WINDOWS':
                addparam = addparam.replace('/','\\')
                insertCommandMaster('EXE.WEBTOB.LICENSE4WIN', [agent_rec.agent_id], addparam)
            elif item.mw_server.os_type.name == 'HPUX':
                insertCommandMaster('RUN.WEBTOB.LICENSE', [agent_rec.agent_id], addparam, out_CID=True)
            else:
                insertCommandMaster('EXE.WEBTOB.LICENSE', [agent_rec.agent_id], addparam)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class WebVhostModelView(ModelView):

    datamodel = SQLAInterface(MwWebVhost)

    list_title   = "WEBTOB VHOST 목록"    
    list_columns = ['mw_web', 'vhost_id', 'web_ports', 'ssl_yn','urlrewrite_yn'\
                    ,'domain_name','host_alias','mw_web_uri','mw_web_server'\
                    ,'mw_web_reverseproxy']
    label_columns = {'mw_web':'WEB'
                    ,'vhost_id':'VHOST ID'
                    ,'web_ports':'Web Port'
                    ,'domain_name':'Domain 이름'
                    ,'host_alias':'HOST ALIAS'
                    ,'urlrewrite_yn':'URL Rewrite 여부'
                    ,'ssl_yn':'SSL 여부'
                    ,'mw_web_uri':'URI'
                    ,'mw_web_server':'Server'
                    ,'mw_web_reverseproxy':'Reverse Proxy'}
                    
    edit_exclude_columns = ['uri_object','create_on']
    add_exclude_columns = ['uri_object','create_on']
    search_exclude_columns = ['uri_object']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    @action("call_url_rewrite","Call URL Rewrite","","fa-rocket",single=False)
    def callUrlRewrote(self, items):

        for item in items:

            agent_rec = getAgent(item.mw_web.agent_id)

            if not agent_rec:
                continue

            insertCommandMaster('READ.URLREWRITE', [agent_rec.agent_id]\
                    , item.urlrewrite_config)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class WebSslModelView(ModelView):

    datamodel = SQLAInterface(MwWebSsl)

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "WEBTOB SSL File 목록"    
    list_columns = ['host_id', 'mw_web.web_name', 'ssl_certi','notbefore','notafter'\
                    ,'t__cn','mw_web_domain','update_dt']
    label_columns = {'host_id':'Host ID'
                    ,'mw_web.web_name':'Web서버'
                    ,'ssl_certi':'SSL Certificate File'
                    ,'notbefore':'시작일'
                    ,'notafter':'만료일'
                    ,'t__cn':'CN'
                    ,'mw_web_domain':'Domain들'
                    ,'update_dt':'확인일시'
                    }
    search_columns = ['host_id', 'notafter', 'update_dt', 'ssl_certi']
                    
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    extra_args = {
        'inputList':[
         {'text':'HOSTNAME','id':'host-name','combind':'0','condition':'_flt_2_host_id=','size':20}
        ]
        }

    @action("call_file_ssl","Call File SSL","","fa-rocket",single=False)
    def callFileSSL(self, items):

        for item in items:

            agent_rec = getAgent(item.mw_web.agent_id)

            if not agent_rec:
                continue

            insertCommandMaster('CALL.GET_SSL_CERTIFILE', [agent_rec.agent_id], item.ssl_certi)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class WebDomainModelView(ModelView):

    datamodel = SQLAInterface(MwWebDomain)

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "WEBTOB Domain 목록"    
    list_columns = ['host_id', 'mw_web_vhost.mw_web.web_name', 't__domain', 'ssl_yn'\
                    ,'t__ssl_certi','notbefore','notafter','t__cn','update_dt']
    label_columns = {'host_id':'Host ID'
                    ,'mw_web_vhost.mw_web.web_name':'Web서버'
                    ,'t__domain':'URL'
                    ,'ssl_yn':'SSL 여부'
                    ,'t__ssl_certi':'SSL Certificate File'
                    ,'notbefore':'시작일'
                    ,'notafter':'만료일'
                    ,'t__cn':'CN'
                    ,'update_dt':'확인일시'
                    }
    search_columns = ['host_id', 'ssl_yn', 'domain_name','notafter'\
                    , 'update_dt', 'ssl_certi']
                    
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    extra_args = {
        'inputList':[
         {'text':'HOSTNAME','id':'host-name','combind':'0','condition':'_flt_2_host_id=','size':20}
        ]
        }

    @action("call_connect_ssl","Call Connect SSL","","fa-rocket",single=False)
    def callConnectSSL(self, items):

        for item in items:

            if item.ssl_yn.name == 'YES':

                agent_rec = getAgent(item.mw_web_vhost.mw_web.agent_id)

                if not agent_rec:
                    continue

                insertCommandMaster('CALL.GET_SSL_CERTI', [agent_rec.agent_id], item.domain_name+':'+item.port)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

    @action("get_connect_ssl","Get Connect SSL","","fa-rocket",single=False)
    def getConnectSSL(self, items):

        for item in items:

            print('Get Connect SSL : ', item.ssl_yn.name, item.mw_web_vhost, item.mw_web_vhost.mw_web, item.mw_web_vhost.mw_web.system_user)
            if item.ssl_yn.name == 'YES':

                createConnectSSL(item.mw_web_vhost.mw_web.agent_id, item.domain_name, item.port)

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class WebServerModelView(ModelView):
    
    datamodel = SQLAInterface(MwWebServer)

    list_title   = "WEBTOB SERVER 목록"    
    list_columns = ['mw_web', 'svr_id', 'svr_type', 'min_proc_count', 'max_proc_count', 'mw_web_vhost', 'mw_was_webtobconnector']
    label_columns = {'mw_web':'WEB'
                    ,'svr_id':'SVR ID'
                    ,'svr_type':'SVR Type'
                    ,'min_proc_count':'session min'
                    ,'max_proc_count':'session max'
                    ,'mw_web_vhost':'V Host'
                    ,'mw_was_webtobconnector':'WAS정보'}

    edit_exclude_columns = ['monitor_now', 'monitor_history', 'create_on']
    add_exclude_columns = ['monitor_now', 'monitor_history', 'create_on']
    search_exclude_columns = ['monitor_now', 'monitor_history'] 
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WebUriModelView(ModelView):
    
    datamodel = SQLAInterface(MwWebUri)

    list_title   = "WEBTOB URI 목록"    
    list_columns = ['mw_web', 'uri_id', 'svr_type', 'uri','mw_web_server','mw_web_vhost']
    label_columns = {'mw_web':'WEB'
                    ,'uri_id':'URI 이름'
                    ,'svr_type':'SVR Type'
                    ,'uri':'URI'
                    ,'mw_web_server':'Server이름'
                    ,'mw_web_vhost':'V Host'}

    edit_exclude_columns = ['create_on']
    add_exclude_columns = ['create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WebReverseproxyModelView(ModelView):
    
    datamodel = SQLAInterface(MwWebReverseproxy)

    list_title   = "WEBTOB REVERSE PROXY 목록"    
    list_columns = ['mw_web', 'reverseproxy_id', 'context_path', 'ssl_yn'\
                    ,'target_ip_address','target_port','target_context_path'\
                    ,'max_connection_count','mw_web_vhost']
    label_columns = {'mw_web':'WEB'
                    ,'reverseproxy_id':'Reverse Proxy 이름'
                    ,'context_path':'Context Path'
                    ,'ssl_yn':'SSL 여부'
                    ,'target_ip_address':'Target IP'
                    ,'target_port':'Target Port'
                    ,'target_context_path':'Target Context Path'
                    ,'max_connection_count':'Max Conn Count'
                    ,'mw_web_vhost':'V Host'
                    }

    edit_exclude_columns = ['create_on']
    add_exclude_columns = ['create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WebchangeHistoryModelView(ModelView):
    
    datamodel = SQLAInterface(MwWebchangeHistory)
    show_template = 'showWithJson.html'
    show_widget  = ShowWithIds

    extra_args = {'buttonList':[
            {'text':'WEB 속성 변경내역','id':'json-button','onclick':'renderJson("Changed Object","WEB 속성 변경내역")'}
          , {'text':'WEB 변경 전 내역','id':'json-button','onclick':'renderJson("Old Httpm Object","WEB 변경 전 내역")'}
        ]}

    list_title   = "WEBTOB Config 변경 이력"    
    list_columns = ['mw_web.host_id', 'mw_web.port', 'create_on']
    label_columns = {'mw_web.host_id':'Host ID'
                    ,'mw_web.port':'Port'
                    ,'create_on':'변경일시'}

    search_columns = ['mw_web','create_on']
    base_order = ('create_on', 'desc')
    base_permissions = ['can_list', 'can_show']
    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class WebModelView(ModelView):
    
    datamodel = SQLAInterface(MwWeb)

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    extra_args = {
        'buttonList':[
         {'text':'운영-차세대','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_newgeneration_yn=YES&_flt_0_landscape=PROD'}
        ,{'text':'운영-유지','id':'toggle_bt2','bt_group':'1','onclick':'_flt_0_newgeneration_yn=NO&_flt_0_landscape=PROD'}
        ,{'text':'개발-차세대','id':'toggle_bt3','bt_group':'1','onclick':'_flt_0_newgeneration_yn=YES&_flt_0_landscape=DEV'}
        ,{'text':'개발-유지','id':'toggle_bt4','bt_group':'1','onclick':'_flt_0_newgeneration_yn=NO&_flt_0_landscape=DEV'}
        ,{'text':'이관-차세대','id':'toggle_bt5','bt_group':'1','onclick':'_flt_0_newgeneration_yn=YES&_flt_0_landscape=TEST'}
        ,{'text':'이관-유지','id':'toggle_bt6','bt_group':'1','onclick':'_flt_0_newgeneration_yn=NO&_flt_0_landscape=TEST'}
        ],
        'selectList':[
         {'text':'Hostname','id':'host-selector','combind':'0','type':'parent'}
        ,{'text':'시스템','id':'tag-selector','combind':'0','type':'parent','condition':{'operator':'and','column':'tag','value':'시스템'}}
        ],
        'inputList':[
         {'text':'WEB 이름','id':'web-name','combind':'0','condition':'_flt_2_web_name=','size':20}
        ]
        }

    list_title   = "WEBTOB 목록"    
    list_columns = ['c_host_id', 'c_ip_address', 'jsv_port', 'colored_landscape','newgeneration_yn'\
                    , 'web_name','colored_built_type', 'system_user', 'c_ssl_yn', 'dependent_was_id'\
                    , 'service_port', 'c_domainInfo_yn', 'view_relationship', 'view_webinfo']
    label_columns = {'c_host_id':'Host ID'
                    ,'jsv_port':'JSV Port'
                    ,'newgeneration_yn':'차세대여부'
                    ,'colored_landscape':'Landscape'
                    ,'web_name':'설명'
                    ,'service_port':'Port'
                    ,'doc_dir':'DOC root'
                    ,'c_ip_address':'IP'
                    ,'colored_built_type':'내장/외장'
                    ,'c_ssl_yn':'SSL설치여부'
                    ,'c_domainInfo_yn':'Domain정보생성'
                    ,'system_user':'서버계정'
                    ,'dependent_was_id':'WAS Domain'
                    ,'view_relationship':'구성도'
                    ,'view_webinfo':'http.m' }

    edit_exclude_columns = ['ssl_object', 'logging_object', 'errordocument_object'\
            , 'proxy_ssl_object', 'tcpgw_object', 'httpm_object','ext_object', 'license_object', 'create_on']
    add_exclude_columns = ['ssl_object', 'logging_object', 'errordocument_object'\
            , 'proxy_ssl_object', 'tcpgw_object', 'httpm_object', 'ext_object', 'license_object', 'create_on']
    search_exclude_columns = ['ssl_object', 'logging_object', 'errordocument_object'\
            , 'proxy_ssl_object', 'tcpgw_object', 'httpm_object', 'ext_object', 'license_object']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    base_order = ('host_id', 'asc')    

    related_views = [WebServerModelView, WebVhostModelView, WebUriModelView, WebReverseproxyModelView]

    @action("call_file_ssl","Call File SSL","","fa-rocket",single=False)
    def callFileSSL(self, items):

        for item in items:

            if item.ssl_object and item.system_user:

                agent_rec = getAgent(item.agent_id)

                if not agent_rec:
                    continue

                for ssl in item.ssl_object:
                    insertCommandMaster('CALL.GET_SSL_CERTIFILE', [agent_rec.agent_id], ssl['CERTIFICATEFILE'])

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())


    @action("get_file_ssl","Get File SSL","","fa-rocket",single=False)
    def getFileSSL(self, items):

        for item in items:

            if item.ssl_object and item.system_user:

                for ssl in item.ssl_object:
                    createFileSSL(item.agent_id, ssl['CERTIFICATEFILE'])

        db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

    @action("multi","Excel Download","","fa-rocket",single=False)
    def myaction(self, items):
        output = BytesIO()
    
        df = pd.read_sql(sql = "select * from mw_web", con = db.session.bind)

        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, 'data', index=False)
        writer.save()
        output.seek(0)
        return send_file(output, attachment_filename='mw_web.xlsx', as_attachment=True)

    @action("create_domain","Create Domain Info","","fa-rocket",single=False)
    def createDomainNameInfo(self, items):

        for item in items:
            host_id = item.host_id
            port    = item.port
            webInfo = {'host_id':host_id, 'port':port}

            createSslInfo(webInfo)
            createDomainNameInfo(webInfo)

            db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())


class BizCategoryModelView(ModelView):
    
    datamodel = SQLAInterface(MwBizCategory)

    list_title   = "업무 구분 목록"    
    list_columns = ['biz_category', 'biz_category_name', 'mw_was', 'mw_web']
    label_columns = {'biz_category':'업무 구분 코드'
                    ,'biz_category_name':'업무 명칭'
                    ,'mw_was':'WAS'
                    ,'mw_web':'WEB'
                    }

    edit_exclude_columns = ['create_on']
    add_exclude_columns = ['create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]
    related_views = [WasModelView, WebModelView]

class DBMasterModelView(ModelView):
    
    datamodel = SQLAInterface(MwDBMaster)

    list_title   = "DB Master"    
    list_columns = ['db_dbms_id', 'landscape', 'vender_name', 'db_server_name', 'db_server_port', 'description', 'mw_app_master']
    label_columns = {'db_dbms_id':'DBMS id'
                    ,'landscape':'Landscape'
                    ,'vender_name':'Vendor'
                    ,'mw_app_master':'Applications'
                    ,'description':'설명'
                    ,'db_server_name':'DB Server'
                    ,'db_server_port':'DB Service port'
                    }

    edit_exclude_columns = ['create_on']
    add_exclude_columns = ['create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

class AppMasterModelView(ModelView):
    
    datamodel = SQLAInterface(MwAppMaster)

    list_template = 'listWithJson.html'

    extra_args = {
        'buttonList':[
         {'text':'운영','id':'toggle_bt1','bt_group':'1','onclick':'_flt_0_landscape=PROD'}
        ,{'text':'개발','id':'toggle_bt2','bt_group':'1','onclick':'_flt_0_landscape=DEV'}
        ],
        'inputList':[
         {'text':'App ID','id':'app-id','combind':'0','condition':'_flt_2_app_id=','size':12}
        ,{'text':'App 이름','id':'app-name','combind':'0','condition':'_flt_2_app_name=','size':12}
        ,{'text':'Host ID','id':'app-server','combind':'0','condition':'_flt_2_app_servers=','size':12}
        ]
        }

    list_title   = "Application Master"    
    list_columns = ['app_id', 'landscape', 'app_name', 'description', 'app_servers','mw_db_master','mw_was_instance']
    label_columns = {'app_id':'App id'
                    ,'landscape':'Landscape'
                    ,'app_name':'App 이름'
                    ,'description':'설명/특이사항'
                    ,'app_servers':'appliaction 설치 서버'
                    ,'mw_db_master':'사용 DB'
                    ,'mw_was_instance':'WAS Instacne'
                    }

    edit_exclude_columns = ['create_on']
    add_exclude_columns = ['create_on']

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]
                    ,['app_id', FilterNotEqual, 'NOAPP']
                    ]

class ServerModelView(ModelView):

    datamodel = SQLAInterface(MwServer)
    
    list_title   = "서버 목록"    
    list_columns = ['host_id', 'server_name', 'colored_landscape', 'ip_address', 'vip_address', 'colored_os'\
                    , 'jdk_version', 'running_type','was_yn', 'web_yn']
    label_columns = {'host_id':'Host Name'
                    ,'server_name':'서버이름'
                    ,'landscape':'Landscape'
                    ,'colored_landscape':'Landscape'
                    ,'os_type':'OS 종류'
                    ,'colored_os':'OS 종류'
                    ,'encoding':'OS엔코딩'
                    ,'jdk_version':'JDK 버전'
                    ,'ip_address':'ip address'
                    ,'vip_address':'vip address'
                    ,'running_type':'A-S 구분'
                    ,'primary_host_id':'Primary서버'
                    ,'mw_was_instance':'WAS'
                    ,'web_yn':'WEB Y/N'
                    ,'was_yn':'WAS Y/N'
                     }

    edit_columns = ['host_id', 'server_name', 'landscape', 'os_type'\
                    , 'encoding', 'ip_address', 'vip_address', 'jdk_version'\
                    ,'running_type', 'primary_host_id']

    add_columns = ['host_id', 'server_name', 'landscape', 'os_type'\
                    , 'encoding', 'ip_address', 'vip_address', 'jdk_version'\
                    ,'running_type', 'primary_host_id']

    search_columns = ['host_id', 'ip_address', 'vip_address', 'landscape', 'running_type']

    base_order = ('host_id', 'asc')    

    base_filters = [['user_id', FilterStartsWithFunction, get_mw_user]]

    related_views = [WasModelView, WebModelView]

    @action("multi","Excel Download","","fa-rocket",single=False)
    def myaction(self, items):
        output = BytesIO()
    
        df = pd.read_sql(sql = "select * from mw_server", con = db.session.bind)

        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, 'data', index=False)
        writer.save()
        output.seek(0)
        return send_file(output, attachment_filename='mw_server.xlsx', as_attachment=True)

class MasterDetailViews(MasterDetailView):
    datamodel = SQLAInterface(MwWas)
    master_div_width = 2
    related_views = [WasInstanceModelView]

class ShortQueries(BaseApi):

    resource_name = 'select'

    @expose('/web_yn/<host_id>/<app_id>', methods=['GET'])
    #@protect()
    def web_yn(self, host_id, app_id):
        print (host_id, app_id)
        return jsonify({'return_code':1}), 201

class MWConfiguration(BaseApi):

    resource_name = 'config'

    @expose('/httpm', methods=['POST'])
    @protect()
    def httpmConfig(self, **kwargs):

        data = json.loads(request.data)

        if not data.get('content'):
            return jsonify({'return_code':-2,'message':'content must be included'}), 401
        elif not data.get('host_id'):
            return jsonify({'return_code':-2,'message':'host_id must be included'}), 401
    
        content   = data['content']
        host_id   = data['host_id']
        system_user = data['system_user'] if data.get('system_user') else ''

        rtn, msg = AutorunResult()._updateHttpm(host_id, content, system_user=system_user)
        db.session.commit()

        return jsonify({'return_code':rtn, 'msg':msg}), 201

    @expose('/jeusdomain', methods=['POST'])
    @protect()
    def jeusDomainConfig(self, **kwargs):

        data = json.loads(request.data)

        if not data.get('content'):
            return jsonify({'return_code':-2,'message':'content must be included'}), 401
        elif not data.get('host_id'):
            return jsonify({'return_code':-2,'message':'host_id must be included'}), 401
        elif not data.get('domain_id'):
            return jsonify({'return_code':-2,'message':'domain_id must be included'}), 401
    
        content   = data['content']
        host_id   = data['host_id']
        domain_id = data['domain_id']
        system_user = data['system_user'] if data.get('system_user') else ''
        
        rtn, msg = AutorunResult()._updateJeusDomain(host_id, domain_id, content, system_user=system_user)
        db.session.commit()

        return jsonify({'return_code':rtn, 'msg':msg}), 201

    @expose('/webmain', methods=['POST'])
    @protect()
    def webmainConfig(self, **kwargs):

        data = json.loads(request.data)

        if not data.get('content'):
            return jsonify({'return_code':-2,'message':'content must be included'}), 401
        elif not data.get('host_id'):
            return jsonify({'return_code':-2,'message':'host_id must be included'}), 401
        elif not data.get('domain_id'):
            return jsonify({'return_code':-2,'message':'domain_id must be included'}), 401
        elif not data.get('was_instance_id'):
            return jsonify({'return_code':-2,'message':'was_instance_id must be included'}), 401
    
        content   = data['content']
        host_id   = data['host_id']
        domain_id = data['domain_id']
        was_instance_id = data['was_instance_id']
        
        rtn, msg = AutorunResult()._updateWebMain(host_id, domain_id, was_instance_id, content)
        db.session.commit()

        return jsonify({'return_code':rtn, 'msg':msg}), 201

class FootPrintApi(BaseApi):

    resource_name = 'footprint'

    @expose('/footprint', methods=['POST'])
#    @protect(allow_browser_login=True)
    def postFootPrint(self, **kwargs):
        data = json.loads(request.data)
        records = data['payLoad']
        [r.update({'ip':request.remote_addr}) for r in records]
        print(records)
        rtn = footprint.insert_many(records)
        print('rtn:',rtn.inserted_ids)
        if rtn:
            return jsonify({'return_code':1}), 201

#class DailyReportModelView(flask_appbuilder.views.ModelView):
class DailyReportModelView(ModelView):
    datamodel = SQLAInterface(DailyReport)

    label_columns = {"file_name": "File Name", "download": "Download"}
    add_columns = ["file", "report_date"]
    edit_columns = ["file", "report_date"]
    list_columns = ["file_name", "download", "report_date"]
    show_columns = ["file_name", "download", "report_date"]

class ServerModelApi(ModelRestApi):
    
    resource_name = 'Server'
    datamodel = SQLAInterface(MwServer)

class JsonView(BaseView):

    route_base = '/json'
    default_view = 'jsonviewer'

    @expose('/htmlviewer/<table_name>/<column_name>/<tcolumn_name>/<key>', methods=['GET'])
    @has_access
    def htmlviewer(self, table_name, column_name, tcolumn_name, key):

        html, _ = selectItem(table_name, column_name, {'id':key})
        title, _ = selectItem(table_name, tcolumn_name, {'id':key})

        return jsonify({'html':html, 'title':title})

    @expose('/jsonviewer/<category>/<key>', methods=['GET'])
    @has_access
    def jsonviewer(self, category, key):

        if category == 'WAS':
            item, _ = selectItem('mw_was', 'was_object', {'was_id':key})
        elif category == 'WEB':
            host_id, port = key.split('__')
            item, _ = selectItem('mw_web', 'httpm_object', {'host_id':host_id,'port':port})

        return jsonify({'json':item})

    @expose('/relationship/<category>/<key>', methods=['GET'])
    @has_access
    def relationship(self, category, key):

        if category == 'WAS':
            json = getWasRelationship(key)
        elif category == 'WEB':
            host_id, port = key.split('__')
            json = getWebRelationship(host_id, int(port))

        return jsonify({'json':json})

class DailyReportApi(ModelRestApi):

    resource_name = 'DailyReport'
    datamodel = SQLAInterface(DailyReport)

class ExampleApi(BaseApi):

    resource_name = 'example'
    greeting_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
                }
            }
        }
    apispec_parameter_schemas = {
            "greeting_schema": greeting_schema
        }

    @expose('/greeting', methods=['GET'])
    @protect(allow_browser_login=True)
    @rison(greeting_schema)    
    def greeting(self, **kwargs):
        """Greeting
        ---
        get:
            responses:
                200:
                    description: 사용자에게 인사하기
                    content:
                        application/json:
                            schema:
                                type: object
                                properties:
                                    message:
                                        type: string
                400:
                    $ref: '#/components/responses/400'
                                        
        """
        if 'name' in kwargs['rison']:
            return self.response(
                200,
                message=f"Hello {kwargs['rison']['name']}"
                )
        return self.response_400(message="잘못된 parameter")

    @expose('/error')
    @protect()
    @safe
    def error(self):
        """Error 500
        ---
        get:
            responses:
                500:
                    $ref: '#/components/responses/500'
        """
        raise Exception

@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )

db.create_all()

appbuilder.add_view(
    ServerModelView,
    "서버 목록",
    icon="fa-folder-open-o",
    category="Server",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    DBMasterModelView,
    "DB Master",
    icon="fa-folder-open-o",
    category="Server",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    AppMasterModelView,
    "App Master",
    icon="fa-folder-open-o",
    category="Server",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    WasModelView,
    "WAS 목록",
    icon="fa-folder-open-o",
    category="Was",
    category_icon="fa-envelope"
)
"""
appbuilder.add_view(
    MasterDetailViews,
    "WAS별 MS 목록",
    icon="fa-envelope",
    category="Was"
)
"""
appbuilder.add_view(
    WasInstanceModelView,
    "JEUS MS 목록",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_view(
    WasHttpListenerModelView,
    "Was Http Listener 목록",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_view(
    WasWebtobConnectorModelView,
    "Was Webtob Connector 목록",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_view(
    DatasourceModelView,
    "Datasource 목록",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_view(
    ApplicationModelView,
    "Application 목록",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_separator("Was")
appbuilder.add_view(
    WaschangeHistoryModelView,
    "WAS Config 변경이력",
    icon="fa-folder-open-o",
    category="Was",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    WasLicenseView,
    "JEUS License 정보",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_view(
    WasLinkView,
    "JEUS WebAdmin Link(차세대-운영)",
    icon="fa-folder-open-o",
    category="Was"
)
appbuilder.add_view(
    WebModelView,
    "WEB 목록",
    icon="fa-folder-open-o",
    category="Web",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    WebServerModelView,
    "Web Server 목록",
    icon="fa-folder-open-o",
    category="Web"
)
appbuilder.add_view(
    WebUriModelView,
    "Web URI 목록",
    icon="fa-folder-open-o",
    category="Web"
)
appbuilder.add_view(
    WebReverseproxyModelView,
    "Reverse Proxy 목록",
    icon="fa-folder-open-o",
    category="Web"
)
appbuilder.add_view(
    WebVhostModelView,
    "Web VHost 목록",
    icon="fa-folder-open-o",
    category="Web"
)
appbuilder.add_view(
    WebSslModelView,
    "SSL FILE 목록",
    icon="fa-folder-open-o",
    category="Web"
)
appbuilder.add_view(
    WebDomainModelView,
    "Domain 이름 목록",
    icon="fa-folder-open-o",
    category="Web"
)
appbuilder.add_separator("Web")
appbuilder.add_view(
    WebchangeHistoryModelView,
    "WEBTOB Config 변경이력",
    icon="fa-folder-open-o",
    category="Web",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    WebLicenseView,
    "WEBTOB License 정보",
    icon="fa-folder-open-o",
    category="Web"
)

"""
appbuilder.add_view(
    MutipleViews,
    "Multi View",
    icon="fa-envelope",
    category="Servers"
)
appbuilder.add_api(HostModelApi)
appbuilder.add_api(JeusContainerModelApi)
appbuilder.add_api(ServerModelApi)
"""
appbuilder.add_api(MWConfiguration)
appbuilder.add_api(ExampleApi)
appbuilder.add_api(FootPrintApi)
appbuilder.add_api(DailyReportApi)
appbuilder.add_api(ServerModelApi)
appbuilder.add_api(ShortQueries)
appbuilder.add_api(JsonView)