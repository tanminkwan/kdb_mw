import logging
from app import appbuilder, db, kafka_producer
from flask import g
from sqlalchemy.sql import select, update, func
from sqlalchemy import null, text, or_, not_, case
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import insert, JSON
from app.models.common import get_uuid
from app.models.agent import AgCommandType, AgCommandMaster, AgCommandDetail\
    , AgResult, AgAgentGroup, AgAgent, AgFile, AgCommandHelper, AgAutorunResult
from app.models.monitor import MoWasInstanceStatus
from .was import getHostId, getDomainIdAsPK
from .monitor import select_row
from sys import exc_info
import json
import re

def getErrorResults(create_on=None):

    recs = None

    if create_on:
        recs = db.session.query(AgResult)\
            .filter(AgResult.create_on>=create_on\
                ,AgResult.result_status.in_(['FAILED','ERROR']))\
                .order_by(AgResult.create_on.desc()).all()
    
    if recs:
        return recs
    else:
        return None 

def getResult(id):

    rec = db.session.query(AgResult).filter(AgResult.id==id).first()

    if rec:
        return rec
    else:
        return None 

def getAutorunFunc(command_id, target_file_name):

    if command_id:

        result = db.session.query(AgAutorunResult)\
            .filter(AgAutorunResult.command_id==command_id\
                ,AgAutorunResult.autorun_type=='COMMAND').first()

        if result:
            return result.autorun_func.name, result.autorun_param

    if target_file_name:

        result = db.session.query(AgAutorunResult)\
            .filter(AgAutorunResult.target_file_name==target_file_name\
                ,AgAutorunResult.autorun_type=='FILENAME').first()

        if result:
            return result.autorun_func.name, result.autorun_param

    return None, None

def createConnectSSL(agent_id, domain_name, port):

    agent_rec = getAgent(agent_id)

    if not agent_rec or not agent_rec.agent_sub_type:
        return 0, ''

    if agent_rec.agent_sub_type.name in ['WIN_JEUS8','WIN_JEUS7']:
        command_type_id = 'RUN.CONNECT.SSL.WIN'
    else:
        command_type_id = 'RUN.CONNECT.SSL'

    insertCommandMaster(command_type_id, [agent_rec.agent_id], domain_name+':'+port, add_CID=True)

def createFileSSL(agent_id, certi_file):

    agent_rec = getAgent(agent_id)

    if not agent_rec or not agent_rec.agent_sub_type:
        return 0, ''

    if agent_rec.agent_sub_type.name in ['WIN_JEUS8','WIN_JEUS7']:
        command_type_id = 'RUN.FILE.SSL.WIN'
    else:
        command_type_id = 'RUN.FILE.SSL'
        
    insertCommandMaster(command_type_id, [agent_rec.agent_id], certi_file, add_CID=True)

def getAgent(agent_id, isApproved=False):

    rec = db.session.query(AgAgent)\
        .filter(func.lower(AgAgent.agent_id)==func.lower(agent_id)).first()

    if rec:
        if not isApproved or rec.approved_yn.name=='YES':
            return rec
        else:
            return None     
    else:
        return None 

def getAgents():

    recs = db.session.query(AgAgent)\
        .filter(AgAgent.approved_yn=='YES').all()

    if recs:
        return recs
    else:
        return None 

def get_agent_stat():

    gap = datetime.now() - timedelta(minutes=3)

    results = db.session.query(\
                AgAgent.landscape, 
                func.sum(1).label('total'), 
                func.sum(case([(AgAgent.last_checked_date<=gap,1)], else_=0)).label('offline')
                )\
                .filter(AgAgent.approved_yn=='YES')\
                .group_by(AgAgent.landscape).all()
    
    recs = db.session.query(AgAgent)\
            .filter(AgAgent.last_checked_date<=gap,AgAgent.approved_yn=='YES')\
            .all()

    if results:
        return results, recs
    else:
        return None, None

def getNextRepetitionSeq(command_id, agent_id):

    result = db.session.query(func.max(AgCommandDetail.repetition_seq))\
                .filter(AgCommandDetail.agent_id==agent_id, AgCommandDetail.command_id==command_id).first()

    if result[0] is None:
        rtn = 1
    else:
        rtn = result[0] + 1
    
    return rtn

def finish_commands(command_ids):

    stmt = update(AgCommandMaster)\
            .where(AgCommandMaster.command_id.in_(command_ids)).values(publish_yn='YES')
    db.session.execute(stmt)

def cancelCommands(command_ids):

    stmt = update(AgCommandMaster)\
            .where(AgCommandMaster.command_id.in_(command_ids)).values(finished_yn='YES')
    db.session.execute(stmt)

def getCommandsToSendNow():

    commandMaster_recs = db.session.query(AgCommandMaster)\
                    .filter(AgCommandMaster.agent_id==agent_id).all()

def getCommandHelper(mapping_key, target_file_name, agent_id):

    commandHelper_recs = db.session.query(AgCommandHelper)\
                    .filter(AgCommandHelper.mapping_key==mapping_key\
                        ,AgCommandHelper.target_file_name==target_file_name\
                        ,AgCommandHelper.agent_id==agent_id).all()

    if commandHelper_recs:        
        return [r.string_to_replace for r in commandHelper_recs]
    else:
        return None

def finish_commands_by_scheduler():

    stmt = update(AgCommandMaster).where(\
                (AgCommandMaster.finished_yn=='NO') \
                & (\
                ((AgCommandMaster.periodic_type == 'IMMEDIATE') & (AgCommandMaster.publish_yn == 'YES'))\
                |((AgCommandMaster.periodic_type == 'ONETIME') & (AgCommandMaster.time_to_exe < datetime.now()))\
                |((AgCommandMaster.periodic_type == 'PERIODIC') & (AgCommandMaster.time_to_stop < datetime.now()))\
                )).values(finished_yn='YES')

    db.session.execute(stmt)

    db.session.commit()

def createCommandDetail(command_id):

    logging.debug(f'Hennry createCommandDetail {command_id}')

    command_rec = db.session.query(AgCommandMaster)\
                .filter(AgCommandMaster.command_id==command_id).first()
  
    command_type_rec = db.session.query(AgCommandType)\
                .filter(AgCommandType.command_type_id==command_rec.command_type_id).first()

    target_file_path = command_type_rec.target_file_path
    target_file_name = command_type_rec.target_file_name

    rexp = re.compile(r'.*?(<<<)(.*?)(>>>)')
    m = rexp.match(target_file_path)
    befor_text = ''

    if m:
        befor_text = m[1]+m[2]+m[3]
            
    # Append all Agents and Agent groups of a command master into a list
    ags = []
    for agg in command_rec.ag_agent_group:
        for ag in agg.ag_agent:
            ags.append(ag)

    ags += command_rec.ag_agent

    # Remove duplicated agents by set func
    for ag in set(ags):

        commandDetail_rec = db.session.query(AgCommandDetail)\
                    .filter(AgCommandDetail.command_id==command_rec.command_id\
                        , AgCommandDetail.agent_id==ag.agent_id\
                        , AgCommandDetail.command_status=='CREATE').first()

        if commandDetail_rec:
            continue

        target_file_paths = []
        if befor_text:

            after_texts = getCommandHelper(m[2], target_file_name, ag.agent_id)

            if after_texts:
                for after_text in after_texts:
                    target_file_paths.append(target_file_path.replace(befor_text, after_text))
                #print("Hennry 4 target_file_path : ", target_file_paths)
            else:
                log.error("StringToReplace not exists : agent_id[%s] befor_text[%s] target_file_name[%s]"\
                        ,ag.agent_id, befor_text, target_file_name)
                continue
        else:
            target_file_paths.append(target_file_path)

        repetition_seq = getNextRepetitionSeq(command_rec.command_id, ag.agent_id)
        log.info('AgCommandDetail KEY SET : [%s][%s][%d]',command_rec.command_id,ag.agent_id,repetition_seq)

        for i, t in enumerate(target_file_paths):

            # REST
            command_status = 'CREATE'

            # Kafka
            if command_rec.command_sender.name == 'KAFKA' and kafka_producer:

                topic = 't_' + ag.agent_id
                key = command_rec.command_id + '_' + str(repetition_seq + i)
                message = dict(
                    command_id        = command_rec.command_id,
                    repetition_seq    = repetition_seq + i,
                    command_class     = command_type_rec.command_class.name,
                    target_file_path  = target_file_paths[i],
                    target_file_name  = target_file_name,
                    additional_params = command_rec.additional_params,
                    result_receiver   = command_rec.result_receiver.name,
                    target_object     = command_rec.target_object,
                    result_hash       = getResultHash(ag.agent_id, command_rec.command_id, repetition_seq + i)
                )

                rtn = kafka_producer.sendMessage(topic, message, key=key)

                if rtn > 0:
                    command_status = 'KAFKA'
                else:
                    command_status = 'KAFKA_FAILED'

            insert_dict = dict(
                    command_id        = command_rec.command_id,
                    agent_id          = ag.agent_id,
                    repetition_seq    = repetition_seq + i,
                    command_type_id   = command_rec.command_type_id,
                    command_class     = command_type_rec.command_class.name,
                    target_file_path  = target_file_paths[i],
                    target_file_name  = target_file_name,
                    additional_params = command_rec.additional_params,
                    command_status    = command_status,
                    user_id           = 'scheduler'
                )
            
            stmt = insert(AgCommandDetail).values(insert_dict)
            r = db.session.execute(stmt)
        
    stmt = update(AgCommandMaster).where(AgCommandMaster.id==command_rec.id).values(publish_yn='YES')
    db.session.execute(stmt)

    return 1, 'OK'

def createCommandDetail_bySch(command_id):

    log.debug('Hennry createCommandDetail_bySch [%s]', command_id)

    try:

        createCommandDetail(command_id)

        db.session.commit()

    except Exception as e:
        excType, excValue, traceback = exc_info()
        log.error('An Error Occured : %s %s %s', excType, excValue, traceback)
        db.session.rollback()

    return 1, 'OK'

def sendCommandImmediately(agent_id, command_type_id):

    return 0, ''

def getOrInsertCommandType(command_class, target_file_path='', target_file_name=''):

    return 0, ''

def insertCommandMaster(command_type_id, agent_ids, additional_param='', add_CID=False, out_CID=False):

    command_id = get_uuid()
    insert_dict = dict(
                      command_id       = command_id
                    , command_type_id  = command_type_id
                    , periodic_type    = 'IMMEDIATE' 
                    , user_id          = 'scheduler'   
                    , publish_yn       = 'YES'                     
                    )

    param = ''

    if additional_param:
        param = additional_param

    if add_CID:
        param += ' ' + command_id
    
    if out_CID:
        param += ' > ' + command_type_id + '.out.' + command_id

    if param:
        insert_dict.update({'additional_params':param})

    stmt = insert(AgCommandMaster).values(insert_dict)
    db.session.execute(stmt)

    commandMaster_rec = db.session.query(AgCommandMaster)\
                    .filter(AgCommandMaster.command_id==command_id).first()

    agent_recs = db.session.query(AgAgent)\
                    .filter(AgAgent.agent_id.in_(agent_ids)).all()

    commandMaster_rec.ag_agent = agent_recs

    createCommandDetail(command_id)

    return 1, ''

def get_closeto_token_expiry_bysch(days):

    subquery = db.session.query(AgCommandDetail.agent_id)\
                    .filter(AgCommandDetail.command_class=='GetRefreshToken',AgCommandDetail.command_status=='CREATE').subquery()

    agent_recs = db.session.query(AgAgent)\
                    .filter(or_(AgAgent.token_expiration_date<=datetime.now()+timedelta(days=days)\
                                ,AgAgent.token_expiration_date==None)\
                            ,~AgAgent.agent_id.in_(subquery)).all()

    if not agent_recs:
        return 0, 'No data is found'

    command_type_rec = db.session.query(AgCommandType)\
                        .filter(AgCommandType.command_class=='GetRefreshToken').first()

    if not command_type_rec:

        command_type_id = 'GetRefreshToken'
        insert_dict = dict(
                      command_type_id   = command_type_id
                    , command_type_name = 'Update Refresh Token'
                    , command_class     = 'GetRefreshToken'
                    , user_id           = 'scheduler'                    
                    )
        stmt = insert(AgCommandType).values(insert_dict)
        db.session.execute(stmt)
    
    else:
        command_type_id = command_type_rec.command_type_id

    command_id = get_uuid()
    insert_dict = dict(
                      command_id       = command_id
                    , command_type_id  = command_type_id
                    , periodic_type    = 'IMMEDIATE' 
                    , user_id          = 'scheduler'   
                    , publish_yn       = 'YES'                     
                    )
    stmt = insert(AgCommandMaster).values(insert_dict)
    db.session.execute(stmt)
    
    ag_command_master_rec = db.session.query(AgCommandMaster)\
                    .filter(AgCommandMaster.command_id==command_id).first()

    logging.debug(f'ag_command_master_rec :{ag_command_master_rec}')

    ag_command_master_rec.ag_agent = agent_recs

    for ag in agent_recs:

        insert_dict = dict(
                    command_id        = command_id,
                    agent_id          = ag.agent_id,
                    repetition_seq    = 1,
                    command_type_id   = command_type_id,
                    command_class     = 'GetRefreshToken',
                    command_status    = 'CREATE',
                    user_id           = 'scheduler'
                    )
        
        stmt = insert(AgCommandDetail).values(insert_dict)
        r = db.session.execute(stmt)

    db.session.commit()

    return 1, 'OK'

def checkAgentAproved(agent_id):

    agent_rec = db.session.query(AgAgent)\
                    .filter(AgAgent.agent_id==agent_id).first()

    if not agent_rec:
        return -1, 'Agent Not Exists'
    elif agent_rec.approved_yn.value == 'NO':
        return -2, 'Not Approved Yet'
    else:
        return 1, 'OK'

def getLatestFile(agent_type, file_name):

    q1 = db.session.query(func.max(AgFile.file_version))\
                .filter(AgFile.agent_type==agent_type, AgFile.file_name==file_name)
    result = db.session.query(AgFile).filter(AgFile.agent_type==agent_type, AgFile.file_name==file_name, AgFile.file_version==q1).first()

    return result.file if result else '' 

def checkAgentUpdated(agent_version):

    return 1, 'OK'

def updateResultStatus(id, status, message):

    db.session.query(AgResult).filter(AgResult.id==id)\
               .update({AgResult.result_status:status\
                        ,AgResult.complited_date:datetime.now()\
                        ,AgResult.result_message:message})

    #db.session.commit()

def updateExpiration(agent_id, expiration_date, refresh_token):

    rtn = db.session.query(AgAgent)\
                    .filter(AgAgent.agent_id==agent_id)\
                    .update({AgAgent.token_expiration_date:expiration_date\
                            ,AgAgent.refresh_token:refresh_token})

    if rtn < 1:
        return -1, 'Agent [' + agent_id + '] : not exists'
        
    db.session.commit()

    return 1, 'OK'

def getResultHash(agent_id, command_id, repetition_seq):

    subquery = db.session.query(func.max(AgResult.repetition_seq))\
                    .filter(AgResult.command_id==command_id\
                            , AgResult.agent_id==agent_id\
                            , AgResult.repetition_seq < repetition_seq\
                            , AgResult.result_hash!=None).subquery()

    query = db.session.query(AgResult.result_hash)\
                    .filter(AgResult.command_id==command_id\
                            , AgResult.agent_id==agent_id\
                            , AgResult.repetition_seq.in_(subquery))

    result_hash_rec = db.session.query(AgResult.result_hash)\
                    .filter(AgResult.command_id==command_id\
                            , AgResult.agent_id==agent_id\
                            , AgResult.repetition_seq.in_(subquery)).first()

    if result_hash_rec:
        result_hash = result_hash_rec[0]
    else:
        result_hash = ""

    return result_hash

def sendCommands(agent_id, agent_version='', agent_type=''):

    data = []
    command_detail_recs = db.session.query(AgCommandDetail)\
                    .filter(AgCommandDetail.agent_id==agent_id, AgCommandDetail.command_status=='CREATE').all()

    for r in command_detail_recs:

        result_hash = getResultHash(agent_id, r.command_id, r.repetition_seq)

        data.append(dict(
                    command_id        = r.command_id,
                    repetition_seq    = r.repetition_seq,
                    command_class     = r.command_class.name,
                    target_file_path  = r.target_file_path,
                    target_file_name  = r.target_file_name,
                    additional_params = r.additional_params,
                    result_receiver   = r.ag_command_master.result_receiver.name,
                    target_object     = r.ag_command_master.target_object,
                    result_hash       = result_hash
                ))

    db.session.query(AgCommandDetail)\
                    .filter(AgCommandDetail.agent_id==agent_id, AgCommandDetail.command_status=='CREATE')\
                    .update({AgCommandDetail.command_status:'SENDED'})

    update_dict = {AgAgent.last_checked_date:datetime.now()}
    if agent_version:
        update_dict.update({AgAgent.agent_version:agent_version})
    if agent_type:
        update_dict.update({AgAgent.agent_type:agent_type})

    db.session.query(AgAgent)\
                    .filter(AgAgent.agent_id==agent_id)\
                    .update(update_dict)

    return 1, data

def addAgent(agent_id, host_id, agent_type, ip_address, installation_path=''):

    insert_dict = dict(
                    agent_id   = agent_id,
                    agent_type = agent_type,
                    host_id    = host_id,
                    ip_address = ip_address,
                    installation_path   = installation_path
                    )
    stmt = insert(AgAgent).values(insert_dict)

    db.session.execute(stmt)
    db.session.commit()

    return 1, 'OK'

"""
def __getTag(agent_id, agent_type, host_id):

    user_id = agent_id[agent_id.find('_')+1:agent_id.rfind('_')]
    tag = 'MWAGENT-' + agent_type + '-' + host_id + '-' + user_id
    tag_id = insertResourceTag('ag_agent', tag)
    return tag_id
"""
def addResult(data):

    result_status = 'FAILED' if data.get('is_normal') and data['is_normal'] == 'false' else 'CREATE'
    command_status = 'FAILED' if data.get('is_normal') and data['is_normal'] == 'false' else 'COMPLITED'

    key_value1  = data['key_value1'] if data.get('key_value1') else 'NO VALUE'
    key_value2  = data['key_value2'] if data.get('key_value2') else 'NO VALUE'

    """
    if key_value1 == 'get_server_stat' and result_status == 'CREATE' :
        rtn, msg = updateWasStatus(key_value2, data['result_text'], data['host_id'])
        if rtn > 0:
            result_status = 'COMPLITED'
        else:
            result_status = 'ERROR'
            log.error("updateWasStatus error : [%s]",msg)
    """
    if data['result_text'] == 'NO CHANGE':
        result_status = 'NOCHANGE'

    #print('data[is_normal] :',data['is_normal'],'rs :',result_status, ' cs :', command_status)
    insert_dict = dict(
                    command_id  = data['command_id'],
                    agent_id    = data['agent_id'],
                    repetition_seq  = data['repetition_seq'],
                    host_id     = data['host_id'],
                    key_value1  = key_value1,
                    key_value2  = key_value2,
                    result_status = result_status,
                    result_hash = data['result_hash'] if data.get('result_hash') else None,
                    result_text = data['result_text']
                    )
    stmt = insert(AgResult).values(insert_dict).returning(AgResult.id)

    result = db.session.execute(stmt)

    result_id = 0
    for r in result:
        result_id = r.id
        break

    db.session.query(AgCommandDetail)\
                    .filter(AgCommandDetail.agent_id==data['agent_id']\
                    , AgCommandDetail.repetition_seq==data['repetition_seq']\
                    , AgCommandDetail.command_id==data['command_id'])\
                    .update({AgCommandDetail.command_status:command_status\
                    ,AgCommandDetail.result_received_date:datetime.now()})

    return 1 if result_status == 'CREATE' else 0, result_id

def getCommandMaster(command_id):

    command_rec = db.session.query(AgCommandMaster)\
                    .filter(AgCommandMaster.command_id==command_id).first()

    return command_rec

def get_commands():

    command_recs = db.session.query(AgCommandMaster)\
                    .filter(AgCommandMaster.cancel_yn=='NO'
                            , AgCommandMaster.finished_yn=='NO'
                            , AgCommandMaster.periodic_type.in_(['ONETIME','PERIODIC'])
                            , or_(AgCommandMaster.periodic_type=='ONETIME', AgCommandMaster.interval_type!=None)
                            , or_(AgCommandMaster.time_to_stop > datetime.now(), AgCommandMaster.time_to_stop==None)
                            , or_(AgCommandMaster.periodic_type=='PERIODIC',AgCommandMaster.time_to_exe > datetime.now(), AgCommandMaster.time_to_exe==None)
                            ).all()

    return command_recs

def getLastRundatetime(command_id):

    result = db.session.query(func.max(AgCommandDetail.create_on))\
                .filter(AgCommandDetail.command_id==command_id).first()

    return result[0]

def updateWasStatus(key_value2, result_text, host_id_of_agent):

    log.info("Hennry1 r_rec.key_value2 : [%s]",key_value2)
    log.info("Hennry1 r_rec.result_text : [%s]",result_text)

    try:
        param_rec  = json.loads(key_value2)
        result_rec = json.loads(result_text)

        # KAFKA STREAM 생성 시 JSON in JSON 인식이 안되는 문제 때문에 이원화됨
        if isinstance(result_rec, dict):
            results = result_rec['servers']
        elif isinstance(result_rec, list):
            results = result_rec

    except json.decoder.JSONDecodeError as e:
        #result_status_list.append('ERROR')
        return -1, 'JSON Parsing error'

    landscape = ''
    update_on = datetime.now()

    real_domain_id = param_rec['jmx_domain']
    url = param_rec['jmx_url']
        
    if url.startswith(('127.0.0.1','localhost')):
        host_id = host_id_of_agent
    else:
        ip_address = url[:url.find(':')]
        host_id = getHostId(ip_address)

        if host_id == ip_address:
            log.error("IP Address dosen't exist in Servers : [%s]",host_id)
        
    domain_id = getDomainIdAsPK(host_id, real_domain_id)

    #print('host_id, real_domain_id, domain_id of getDomainIdAsPK: ',host_id, real_domain_id, domain_id)
    was_rec, _ = ('mw_was', {'was_id':domain_id})

    if was_rec and was_rec.landscape:
        landscape = was_rec.landscape.name
    else:
        return -1, 'Landscape is not defined'

    for stat_r in results:

        # KAFKA STREAM 생성 시 JSON Array 인식이 안되는 문제 때문에 이원화됨
        if isinstance(stat_r, dict):
            d_server_name = stat_r['server_name']
            d_status      = stat_r['status']
        else:
            [d_server_name, d_status] = stat_r.split('__')

        if d_status in ['RUNNING','STANDBY','SHUTDOWN','FAILED']:
            was_instance_status = d_status
        elif d_status == 'READY':
            #status:1 RUNNING, 0: FAIL
            AppNotDeployed = next((True for app in stat_r['application_status']\
                                     if app['status']!='1'), False)
            if AppNotDeployed:
                was_instance_status = 'STANDBY'
            else:
                was_instance_status = 'RUNNING'
        else:
            was_instance_status = 'FAILED'

        update_dict = dict(
            host_id             = was_rec.located_host_id,
            was_instance_status = was_instance_status,
            landscape           = landscape,
            update_on           = update_on
        )
            
        insert_dict = update_dict.copy()
        insert_dict.update(
            was_id          = domain_id,
            was_instance_id = d_server_name,
            user_id         = 'scheduler'
        )

        stmt = insert(MoWasInstanceStatus).values(insert_dict)    
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=['was_id', 'was_instance_id'],
            set_=update_dict
        )
        db.session.execute(do_update_stmt)

    return 1, 'OK'

