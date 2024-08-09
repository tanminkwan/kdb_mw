from app import appbuilder, db, KAFKA_BROKERS, KAFKA_CONSUMER_4_WAS_MONITORING\
        , kafka_producer, WAS_STATUS, consumer4WasMonitoring
from app.models.was import MwWasWebtobConnector, MwWebServer, MwWas, MwWeb, MwWebVhost\
        , MwWebDomain, MwWebSsl
from .was import getWebServers
from .knowledge import insert_tag
from .agent import finishCommands, getAgent
from .monitor import update_rows, insert_row, select_rows, select_row, getWasStatusTemplate
from sqlalchemy.dialects.postgresql import insert
import re, json
from app.auto_report.auto_report import run_auto_report
from datetime import datetime, timedelta
from app.kafka_customer import Consumer4Kafka

def runBatch_bySch(command_id, function_name, fix_param, additional_param=''):

    if function_name == 'createWebtobConn':
        createWebtobConn(additional_param)
    elif function_name == 'createDomainNameInfo':
        print('HH additional_param:',fix_param ,':',additional_param)
        createDomainNameInfo(additional_param)
    elif function_name == 'sendDailyReport':
        sendDailyReport(int(additional_param) if additional_param else 0)
    elif function_name == 'updateUrlRewriteInfo':
        updateUrlRewriteInfo()
    elif function_name == 'updateAgentIdInfoInWeb':
        updateAgentIdInfoInWeb()
    elif function_name == 'updateAgentIdInfoInWas':
        updateAgentIdInfoInWas()
    elif function_name == 'produceRepeatedMessage':
        dic_items = json.loads(additional_param)
        produceRepeatedMessage(dic_items['topic']
                        , dic_items['message']
                        , dic_items['key'] if dic_items.get('key') else None)
    elif function_name == 'updateWasStatus':
        updateWasStatus()
    elif function_name == 'stopUpdateWasStatus':
        stopUpdateWasStatus()
    elif function_name == 'deleteKafkaTopic':
        deleteKafkaTopic(additional_param)
    elif function_name == 'updateResourceTag':
        updateResourceTag()

    finishCommands([command_id])
    db.session.commit()
    print("finished job : ", function_name)

    return 1, 'OK'

def updateResourceTag():

    #_updateResourceTag('ag_agent')
    #_updateResourceTag('mw_was')
    #_updateResourceTag('mw_web')
    __updateResourceTag()
    #updateWASResourceTag()
    #updateWEBResourceTag()

def __updateResourceTag():

    recs, _ = select_rows('mw_was_instance', {})

    for rec in recs:

        if '_Domain' in rec.was_id and '_M' in rec.was_instance_id:
            tag1 = rec.was_id.replace('_Domain','')[1:]
            tag2 = rec.was_instance_id.split('_M')[0]
            tag = 'MS-' + tag1 + '_Domain-' + tag2
            tag_id = __upsertTag(tag)
            row, _ = select_row('ut_tag',{'id':tag_id})
            rec.ut_tag = [row]

def __upsertTag(tag):

    rtn = insert_tag(tag)
    return rtn
           
"""
def _getResourceTag(table_name, rec):

    if table_name == 'ag_agent':
        agent_id = rec.agent_id
        user_id = agent_id[agent_id.find('_')+1:agent_id.rfind('_')]
        resource_tag = 'MWAGENT-' + rec.agent_type.name + '-' + rec.host_id + '-' + user_id
    elif table_name == 'mw_was':
        resource_tag = 'WAS-' + rec.was_id + '-' + rec.located_host_id + '-' + (rec.sys_user if rec.sys_user else 'NOUSERID')
    elif table_name == 'mw_web':
        resource_tag = 'WEB-' + rec.host_id + '-' + str(rec.port) + '-' + (rec.sys_user if rec.sys_user else 'NOUSERID')
    elif table_name == 'mw_was_instance':
        resource_tag = 'MS-' + rec.was_id + '-' + rec.host_id + '-' + rec.was_instance_id.replace('_MS','_MS-')

    return resource_tag

"""
def stopUpdateWasStatus():

    if consumer4WasMonitoring:
        consumer4WasMonitoring.close()

def updateWasStatus():

    # 모니터링대상 WAS List 조회
    recs, groups = getWasStatusTemplate()

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
    
    return 1, ''

def deleteKafkaTopic(topic):

    if kafka_producer:
        kafka_producer.deleteTopic(topic)

def produceRepeatedMessage(topic, message, key):

    if kafka_producer:
        kafka_producer.send_message(topic, message, key=key)

def sendDailyReport(daygap):

    sender      = 'o2000988@gwe.kdb.co.kr'
    sender_name = 'LBS Scheduler'
    receivers   = ['o2000988@gwe.kdb.co.kr','o2000990@gwe.kdb.co.kr','o2000866@gwe.kdb.co.kr','o1404902@gwe.kdb.co.kr']
    ccs         = ['o2000866@gwe.kdb.co.kr']

    theDay = datetime.now() + timedelta(days=daygap)
    weekDay = theDay.weekday()

    if weekDay == 5:
        daygap+=2
    elif weekDay == 6:
        daygap+=1

    run_auto_report(sender, sender_name, receivers, ccs, daygap)

def createSslInfo(webInfo):

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

def updateAgentIdInfoInWeb():

    print('updateAgentIdInfoInWeb started')
    web_recs = db.session.query(MwWeb).all()

    if not web_recs:
        return 0, ''

    for rec in web_recs:

        update_dict = {'agent_id':__getAgent(rec.sys_user, rec.host_id)}
        filter_dict = dict(
            host_id = rec.host_id
           ,port    = rec.port
        )
        updateRows('mw_web', update_dict, filter_dict)

    return 1, 'OK'

def updateAgentIdInfoInWas():

    print('updateAgentIdInfoInWas started')
    was_recs = db.session.query(MwWas).all()

    if not was_recs:
        return 0, ''

    for rec in was_recs:

        update_dict = {'agent_id':__getAgent(rec.sys_user, rec.located_host_id)}
        filter_dict = dict(
            was_id     = rec.was_id
        )
        updateRows('mw_was', update_dict, filter_dict)

    return 1, 'OK'

def __getAgent(sys_user, host_id):
    rec = getAgent(host_id + '_' + sys_user + '_J', isApproved=True)
    return rec.agent_id if rec else ''

def updateUrlRewriteInfo():

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

            updateRows('mw_web_vhost',update_dict, filter_dict)

def createDomainNameInfo(webInfo):

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

def createWebtobConn(domain_id=''):

    #print('HHH 14 :', createWebtobConn)    

    query = db.session.query(MwWasWebtobConnector)

    if domain_id:
        query = query.filter(MwWasWebtobConnector.was_id==domain_id)

    result = query.all()

    for r in result:

        web_recs = getWebServers(r)

        if web_recs:
            r.mw_web_server = web_recs
        else:
            r.mw_web_server = []

