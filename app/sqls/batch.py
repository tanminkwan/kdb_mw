from app import appbuilder, db, KAFKA_BROKERS, KAFKA_CONSUMER_4_WAS_MONITORING\
        , kafka_producer, WAS_STATUS, consumer4WasMonitoring
from app.models.was import MwWasWebtobConnector, MwWebServer, MwWas, MwWeb, MwWebVhost\
        , MwWebDomain, MwWebSsl
from app.views.common import call_notification
from .relationship import get_web_servers
from .knowledge import insert_tag
from .agent import finish_commands, get_agent
from .monitor import update_rows, insert_row, select_rows, select_row, get_was_status_template, \
    get_not_running_was_list
from sqlalchemy.dialects.postgresql import insert
#from app.auto_report.auto_report import run_auto_report
from datetime import datetime, timedelta
#from app.kafka.kafka_customer import Consumer4Kafka
from datetime import datetime
import re, json
import functools
import inspect
import logging

batch_function_registry = {}

def batch_function(func):
    @functools.wraps(func)
    def batch_wrapper(command_id, *args, **kwargs):
        logging.debug(f"시작: {func.__name__} - {datetime.now()}")
        try:
            # 원래 함수 실행
            result = func(*args, **kwargs)
            
            # run_batch_by_scheduler 기능 수행
            finish_commands([command_id])
            db.session.commit()

            logging.debug(f"작업 완료: {func.__name__}")
            return 1, 'OK'
        except Exception as e:
            logging.error(f"오류 발생: {func.__name__} - {e}")
            return 0, str(e)
    
    # Register the function in the global registry immediately
    batch_function_registry[func.__name__] = func.__doc__ or func.__name__
    
    return batch_wrapper

def run_batch_by_scheduler(command_id, function_name, additional_param=''):
    try:
        # 전역 네임스페이스에서 함수 찾기
        func = globals()[function_name]
        if callable(func):
            # Check the number of parameters the function expects
            func_signature = inspect.signature(func)
            param_count = len(func_signature.parameters)

            if param_count == 0:
                return func(command_id)
            elif param_count == 1:
                return func(command_id, additional_param)
            else:
                return 0, f"'{function_name}'에 허용되지 않는 인수 수입니다."
        else:
            return 0, f"'{function_name}'은(는) 호출 가능한 함수가 아닙니다."
    except KeyError:
        return 0, f"함수 '{function_name}'을(를) 찾을 수 없습니다."
    except Exception as e:
        return 0, f"함수 실행 중 오류 발생: {str(e)}"

@batch_function
def update_resource_tag():
    """mw_was_instance tag 일괄 update"""
    #_update_resource_tag('ag_agent')
    #_update_resource_tag('mw_was')
    #_update_resource_tag('mw_web')
    _update_resource_tag()
    #update_was_resource_tag()
    #update_web_resource_tag()

def _update_resource_tag():

    recs, _ = select_rows('mw_was_instance', {})

    for rec in recs:

        if '_Domain' in rec.was_id and '_M' in rec.was_instance_id:
            tag1 = rec.was_id.replace('_Domain','')[1:]
            tag2 = rec.was_instance_id.split('_M')[0]
            tag = 'MS-' + tag1 + '_Domain-' + tag2
            tag_id = _upsert_tag(tag)
            row, _ = select_row('ut_tag',{'id':tag_id})
            rec.ut_tag = [row]

def _upsert_tag(tag):

    rtn = insert_tag(tag)
    return rtn

@batch_function
def notify_was_abnormal_status():
    _, recs, _ = get_not_running_was_list()

    logging.info(f"was_abnormal_status 건수 : {len(recs)}")
    [ call_notification(f"WAS_STATUS:{rec['was_instance_id']}-상태 비정상({rec['was_instance_stat']}.{rec['host_id']})") for rec in recs]

@batch_function
def stop_update_was_status():
    """Kafka  : Stop WAS Monistoring"""
    if consumer4WasMonitoring:
        consumer4WasMonitoring.close()

@batch_function
def update_was_status():
    """Updating WAS_STATUS"""
    # 모니터링대상 WAS List 조회
    recs, groups = get_was_status_template()

    for rec in recs:
        tmp_dict = dict(
            DOMAIN_ID = rec['was_id'],
            HOST_ID = rec['host_id'].upper(),
            SERVER_NAME = rec['was_instance_id'],
            WAS_INSTANCE_GROUP = rec['was_instance_group']
        )
        WAS_STATUS.update(
            #{rec['was_id']+'.'+rec['host_id'].upper()+'.'+rec['was_instance_id']:tmp_dict}
            {rec['was_id']+'.'+rec['was_instance_id']:tmp_dict}
            )
        WAS_STATUS.update(
            {'GROUPS':groups}
            )

    # 모니터링 정보 update (on going)
    '''
    global consumer4WasMonitoring
    #consumer4WasMonitoring = Consumer4Kafka(['10.6.16.102:9092'], 'S_PROD_JMX_RESULT_BY_SERVER', KAFKA_CONSUMER_4_WAS_MONITORING)
    consumer4WasMonitoring = Consumer4Kafka(KAFKA_BROKERS, 'S_PROD_JMX_RESULT_BY_SERVER', KAFKA_CONSUMER_4_WAS_MONITORING)
    
    consumer4WasMonitoring.seekToEnd()

    for _, val in consumer4WasMonitoring.getMessage():

        key = val['DOMAIN_ID']+'.'+val['SERVER_NAME']
        if WAS_STATUS.get(key):
            val.update(dict(
                UPDATE_DATE        = datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                WAS_INSTANCE_GROUP = WAS_STATUS[key]['WAS_INSTANCE_GROUP']
                ))
            WAS_STATUS[key] = val
    '''
    return 1, ''

@batch_function
def delete_kafka_topic(topic):
    """Delete Kafka Topic"""
    if kafka_producer:
        kafka_producer.deleteTopic(topic)

@batch_function
def produce_repeated_message(additional_param):
    dic_items = json.loads(additional_param)
    topic     = dic_items['topic']
    message   = dic_items['message']
    key       = dic_items['key'] if dic_items.get('key') else None
    
    if kafka_producer:
        kafka_producer.send_message(topic, message, key=key)

@batch_function
def update_agent_id_info_in_web():

    print('updateAgentIdInfoInWeb started')
    web_recs = db.session.query(MwWeb).all()

    if not web_recs:
        return 0, ''

    for rec in web_recs:

        update_dict = {'agent_id':_get_agent(rec.sys_user, rec.host_id)}
        filter_dict = dict(
            host_id = rec.host_id
           ,port    = rec.port
        )
        update_rows('mw_web', update_dict, filter_dict)

    return 1, 'OK'

@batch_function
def update_agent_id_info_in_was():

    print('updateAgentIdInfoInWas started')
    was_recs = db.session.query(MwWas).all()

    if not was_recs:
        return 0, ''

    for rec in was_recs:

        update_dict = {'agent_id':_get_agent(rec.sys_user, rec.located_host_id)}
        filter_dict = dict(
            was_id     = rec.was_id
        )
        update_rows('mw_was', update_dict, filter_dict)

    return 1, 'OK'

def _get_agent(sys_user, host_id):
    rec = get_agent(host_id + '_' + sys_user + '_J', isApproved=True)
    return rec.agent_id if rec else ''

@batch_function
def update_url_rewrite_info():

    print('updateUrlRewriteInfo started')
    web_recs = db.session.query(MwWeb).all()

    if not web_recs:
        return 0, ''

    for rec in web_recs:

        httpm = rec.httpm_object
        if not httpm or not httpm.get('VHOST'):
            continue
        
        for vh in httpm['VHOST']:

            if not vh.get('URLREWRITE') or vh['URLREWRITE'] in ['N', 'n']:
                update_dict = dict(
                    urlrewrite_yn     = 'NO'
                )
            else:

                urlrewrite_config = vh['URLREWRITECONFIG'] if vh.get('URLREWRITECONFIG') else ''

                if '${WEBTOBDIR}' in urlrewrite_config:
                    urlrewrite_config = urlrewrite_config.replace('${WEBTOBDIR}', rec.web_home)

                update_dict = dict(
                    urlrewrite_yn     = 'YES'
                   ,urlrewrite_config = urlrewrite_config
                )

            filter_dict = dict(
                host_id  = rec.host_id
               ,port     = rec.port
               ,vhost_id = vh['NAME']
            )

            update_rows('mw_web_vhost',update_dict, filter_dict)

@batch_function
def create_domain_name_info(webInfo):
    return _create_domain_name_info(webInfo)

def _create_domain_name_info(webInfo):

    if not webInfo:
        return 0, 'Parameters don\'t exist'

    if isinstance(webInfo, str):
        wi = eval(webInfo)
    else:
        wi = webInfo

    web_rec = db.session.query(MwWeb)\
                .filter(MwWeb.host_id==wi['host_id'], MwWeb.port==wi['port'])\
                .first()

    if not web_rec:
        return 0, ''

    httpm = web_rec.httpm_object
    ssls  = web_rec.ssl_object

    vhost_recs = db.session.query(MwWebVhost)\
                .filter(MwWebVhost.mw_web_id==web_rec.id).all()

    if not vhost_recs:
        return 0, ''

    domain_name_list = []
    domain_name_dict = {}

    for v in vhost_recs:

        domains = []
        if v.domain_name:
            domains += v.domain_name.split(',')
        if v.host_alias:
            domains += v.host_alias.split(',')

        domains = list(set(domains))
        ports = v.web_ports.replace(' ','').split(',')

        ssl_yn = 'NO'
        ssl_certiFile    = ''
        ssl_certiKeyFile = ''
        ssl_CACertiFile  = ''

        ssl_recs = None

        if v.ssl_yn.name == 'YES':
            ssl_yn = 'YES'

            ssl_rec = db.session.query(MwWebSsl)\
                .filter(MwWebSsl.mw_web_id==web_rec.id\
                      , MwWebSsl.ssl_name==v.ssl_name\
                      ).first()

        for domain in domains:

            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain):
                continue

            for port in ports:

                update_dict = dict( ssl_yn      = ssl_yn
                                  , user_id     = 'scheduler'
                                  , create_on   = datetime.now()
                )

                insert_dict = update_dict.copy()
                insert_dict.update( host_id     = wi['host_id']
                                  , mw_web_vhost_id = v.id
                                  , domain_name = domain
                                  , port        = port
                )

            stmt = insert(MwWebDomain).values(insert_dict)    
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['mw_web_vhost_id', 'domain_name', 'port'],
                set_=update_dict
            ).returning(MwWebDomain.id)
            rtn = db.session.execute(do_update_stmt)

            if ssl_yn == 'YES' and ssl_rec:

                domain_id = None
                for rec in rtn:
                    domain_id = rec[0]

                domain_rec = db.session.query(MwWebDomain)\
                    .filter(MwWebDomain.id==domain_id).first()

                domain_rec.mw_web_ssl = [ssl_rec]

    return 1, 'OK'

@batch_function
def create_webtob_conn(domain_id=''):

    #print('HHH 14 :', createWebtobConn)    

    query = db.session.query(MwWasWebtobConnector)

    if domain_id:
        query = query.filter(MwWasWebtobConnector.was_id==domain_id)

    result = query.all()

    for r in result:

        web_recs = get_web_servers(r)

        if web_recs:
            r.mw_web_server = web_recs
        else:
            r.mw_web_server = []


@batch_function
def create_ssl_info(webInfo):
    return _create_ssl_info(webInfo)

def _create_ssl_info(webInfo):

    if not webInfo:
        return 0, ''

    if isinstance(webInfo, str):
        wi = eval(webInfo)
    else:
        wi = webInfo

    web_rec = db.session.query(MwWeb)\
                .filter(MwWeb.host_id==wi['host_id'], MwWeb.port==wi['port'])\
                .first()

    if not web_rec:
        return 0, ''

    ssls  = web_rec.ssl_object

    ssl_name      = ''
    ssl_certi     = ''
    ssl_certikey  = ''
    ssl_cacerti   = ''
    ssl_protocols = ''
    ssl_ciphers   = ''

    for ssl in ssls:

        ssl_name     = ssl['NAME']\
                        if ssl.get('NAME') else ''
        ssl_certi    = ssl['CERTIFICATEFILE']\
                        if ssl.get('CERTIFICATEFILE') else ''
        ssl_certikey = ssl['CERTIFICATEKEYFILE']\
                        if ssl.get('CERTIFICATEKEYFILE') else ''
        ssl_cacerti  = ssl['CACERTIFICATEFILE']\
                        if ssl.get('CACERTIFICATEFILE') else ''
        ssl_protocols= ssl['PROTOCOLS']\
                        if ssl.get('PROTOCOLS') else ''
        ssl_ciphers  = ssl['REQUIREDCIPHERS']\
                        if ssl.get('REQUIREDCIPHERS') else ''

        update_dict = dict( ssl_certi     = ssl_certi
                          , ssl_certikey  = ssl_certikey
                          , ssl_cacerti   = ssl_cacerti
                          , ssl_protocols = ssl_protocols
                          , ssl_ciphers   = ssl_ciphers
                          , user_id       = 'scheduler'
                          , create_on     = datetime.now()
            )

        insert_dict = update_dict.copy()
        insert_dict.update( host_id  = wi['host_id']
                          , mw_web_id = web_rec.id
                          , ssl_name  = ssl_name
                )

        stmt = insert(MwWebSsl).values(insert_dict)    
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=['mw_web_id', 'ssl_name'],
            set_=update_dict
        )
        db.session.execute(do_update_stmt)

    return 1, 'OK'

updateResourceTag = update_resource_tag
updateWasStatus = update_was_status
updateAgentIdInfoInWeb = update_agent_id_info_in_web
updateAgentIdInfoInWas = update_agent_id_info_in_was
updateUrlRewriteInfo = update_url_rewrite_info
stopUpdateWasStatus = stop_update_was_status
deleteKafkaTopic = delete_kafka_topic
createDomainNameInfo = create_domain_name_info
createSslInfo = create_ssl_info
createWebtobConn = create_webtob_conn
produceRepeatedMessage = produce_repeated_message

for old_name, new_func in [
    ('updateResourceTag', update_resource_tag),
    ('updateWasStatus', update_was_status),
    ('updateAgentIdInfoInWeb', update_agent_id_info_in_web),
    ('updateAgentIdInfoInWas', update_agent_id_info_in_was),
    ('updateUrlRewriteInfo', update_url_rewrite_info),
    ('stopUpdateWasStatus', stop_update_was_status),
    ('deleteKafkaTopic', delete_kafka_topic),
    ('createDomainNameInfo', create_domain_name_info),
    ('createSslInfo', create_ssl_info),
    ('createWebtobConn', create_webtob_conn),
    ('produceRepeatedMessage', produce_repeated_message),
]:
    batch_function_registry[old_name] = new_func.__doc__ or old_name

# ---- Role/Permission Sync ----

# 메뉴 카테고리 → role 매핑. Was/Web은 mw_rgroup으로 통합.
MENU_CATEGORY_TO_ROLE = {
    'Server':        'server_rgroup',
    'Was':           'mw_rgroup',
    'Web':           'mw_rgroup',
    'Agent&Command': 'agent_rgroup',
    'Monitor':       'monitor_rgroup',
    'System':        'system_rgroup',
    '지식관리':       'knowledge_rgroup',
    'ITAM 대사':     'itam_rgroup',
    'Tools':         'tools_rgroup',
}

# 모든 유저가 기본적으로 가져야 할 공통 권한 (Home, 프로필 등)
COMMON_VIEWS_FOR_ALL = [
    'MyIndexView', 'UserDBModelView', 'ResetPasswordView', 
    'UserInfoEditView', 'CommonView'
]

@batch_function
def sync_role_permissions():
    """메뉴 및 API 기반 Role 자동 생성 및 권한 할당"""
    sm = appbuilder.sm
    role_perms = {}  # {role_name: set of (permission_name, view_menu_name)}

    def add_perms_for_view(role_name, view):
        """View 및 관련된 모든 권한(PVM)을 수집하여 role_perms에 추가"""
        if not view:
            return
        
        # 검색할 ViewMenu 이름 후보군
        v_names = set()
        v_names.add(view.__class__.__name__)
        if hasattr(view, 'view_name'):
            v_names.add(view.view_name)
        
        for name in v_names:
            if not name: continue
            pvm_list = db.session.query(sm.permissionview_model)\
                .join(sm.viewmenu_model)\
                .filter(sm.viewmenu_model.name == name).all()
            for pvm in pvm_list:
                if pvm.permission and pvm.view_menu:
                    role_perms[role_name].add((pvm.permission.name, pvm.view_menu.name))
        
        # related_views(상세 보기 등)에 대한 권한도 포함
        if hasattr(view, 'related_views'):
            for related_view_class in view.related_views:
                rv_name = related_view_class.__name__
                pvm_list = db.session.query(sm.permissionview_model)\
                    .join(sm.viewmenu_model)\
                    .filter(sm.viewmenu_model.name == rv_name).all()
                for pvm in pvm_list:
                    if pvm.permission and pvm.view_menu:
                        role_perms[role_name].add((pvm.permission.name, pvm.view_menu.name))

    # 1. 메뉴 기반 처리
    for menu_item in appbuilder.menu.menu:
        category_name = menu_item.name
        role_name = MENU_CATEGORY_TO_ROLE.get(category_name)
        if not role_name:
            continue

        if role_name not in role_perms:
            role_perms[role_name] = set()

        # 카테고리 메뉴 자체 접근권한
        role_perms[role_name].add(('menu_access', category_name))

        # 하위 메뉴 아이템 처리
        if hasattr(menu_item, 'childs'):
            for child in menu_item.childs:
                if hasattr(child, 'name') and child.name:
                    # 메뉴 접근 권한
                    role_perms[role_name].add(('menu_access', child.name))

                    # View 및 연관 View(related_views)의 모든 권한 수집
                    if hasattr(child, 'baseview') and child.baseview:
                        add_perms_for_view(role_name, child.baseview)

    # 2. API 기반 처리 (api_rgroup) - BaseApi 상속 클래스 동적 수집
    if 'api_rgroup' not in role_perms:
        role_perms['api_rgroup'] = set()
    
    from flask_appbuilder.api import BaseApi
    for view in appbuilder.baseviews:
        if isinstance(view, BaseApi):
            api_class_name = view.__class__.__name__
            pvm_list = db.session.query(sm.permissionview_model)\
                .join(sm.viewmenu_model)\
                .filter(sm.viewmenu_model.name == api_class_name).all()
            for pvm in pvm_list:
                if pvm.permission and pvm.view_menu:
                    role_perms['api_rgroup'].add((pvm.permission.name, pvm.view_menu.name))

    # 3. 공통 기반 role 처리 (common_rgroup) - 로그인 및 기본 UI 유지용
    if 'common_rgroup' not in role_perms:
        role_perms['common_rgroup'] = set()
    
    for v_name in COMMON_VIEWS_FOR_ALL:
        pvm_list = db.session.query(sm.permissionview_model)\
            .join(sm.viewmenu_model)\
            .filter(sm.viewmenu_model.name == v_name).all()
        for pvm in pvm_list:
            if pvm.permission and pvm.view_menu:
                role_perms['common_rgroup'].add((pvm.permission.name, pvm.view_menu.name))
    
    # MyIndexView 에 대한 menu_access 는 명시적으로 추가 (등록 안되어 있을 수 있음)
    role_perms['common_rgroup'].add(('menu_access', 'Main'))
    role_perms['common_rgroup'].add(('menu_access', 'MyIndexView'))

    # 4. Role 생성/업데이트
    results = []
    for role_name, perms in role_perms.items():
        role = sm.find_role(role_name)
        if not role:
            role = sm.add_role(role_name)
            results.append(f"Created role: {role_name}")
        else:
            results.append(f"Updated role: {role_name}")

        # 기존 권한 초기화 후 업데이트
        role.permissions = []
        for perm_name, view_name in perms:
            pvm = sm.find_permission_view_menu(perm_name, view_name)
            if pvm:
                sm.add_permission_role(role, pvm)

    summary = '; '.join(results)
    logging.info(f"sync_role_permissions: {summary}")
    return 1, summary


