import logging
import json
import sys
from io import BytesIO
from datetime import datetime, timedelta
from flask import g, request, jsonify, send_file
from flask_appbuilder.api import BaseApi, expose, protect
from flask_jwt_extended import create_refresh_token

from app import appbuilder, db, KAFKA_BROKERS
from app.sqls.agent_dml import AutorunResult
from app.file_manager.s3.filemanager import S3FileManager
from app.sqls.agent import (
    check_agent_approved,
    check_agent_updated,
    send_commands,
    add_result,
    add_agent,
    get_latest_file,
    update_expiration
)

class CommandApi(BaseApi):

    resource_name = 'command'

    @expose('/<agent_id>/<agent_version>', methods=['GET'])
    @protect()
    def command(self, agent_id, agent_version):

        logging.debug(f"command is called. agent_id / agent_version : {agent_id} / {agent_version}")

        rtn , msg = check_agent_approved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , msg = check_agent_updated(agent_version)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = send_commands(agent_id, agent_version)

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/<agent_id>/<agent_version>/<agent_type>', methods=['GET'])
    @protect()
    def command_v2(self, agent_id, agent_version, agent_type):
        
        rtn , msg = check_agent_approved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , msg = check_agent_updated(agent_version)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = send_commands(agent_id, agent_version, agent_type)

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/<agent_id>/<agent_version>/<agent_type>/<agent_status>', methods=['GET'])
    @protect()
    def command_v4(self, agent_id, agent_version, agent_type, agent_status):

        logging.debug(f"command_v4 is called. agent_id : {agent_id}")

        rtn , msg = check_agent_approved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , msg = check_agent_updated(agent_version)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = send_commands(agent_id, agent_version, agent_type)

        #최초 접속인 경우
        if agent_status == 'BOOT':
            data.append(dict(
                        command_class     = 'BOOT',
                        kafka_broker_address = ','.join(KAFKA_BROKERS)
                    ))

        db.session.commit()

        logging.debug(f"command_v4 returned data : {data}")

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/<agent_id>', methods=['GET'])
    @protect()
    def command_v3(self, agent_id):

        logging.debug(f"command_v3 is called. agent_id : {agent_id}")

        rtn , msg = check_agent_approved(agent_id)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg}), 201

        rtn , data = send_commands(agent_id)

        db.session.commit()

        return jsonify({'return_code':rtn, 'message':'OK', 'data':data}), 200

    @expose('/result', methods=['POST'])
    @protect()
    def agent(self, **kwargs):

        data = json.loads(request.data)

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

        rtn , result_id = add_result(data)

        db.session.commit()

        #Result 상태가 'CREATE' 인 경우 Auto Run Result 수행
        if rtn > 0:

            msg = ''
            try:
                ar = AutorunResult(result_id=result_id)
                rtn2, msg = ar.call_autorun_func()
            except Exception as e:
                excType, excValue, traceback = sys.exc_info()
                logging.error(f'call_autorun_func Error : 1{excType} 2{excValue} 3{traceback}')
                rtn2 = -1

            if rtn2 > 0:
                db.session.commit()
            else:
                command_id = data.get('command_id')
                logging.error(f'call_autorun_func [command_id:{command_id}][msg:{msg}]')
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

        rtn , msg = add_agent(agent_id, host_id, agent_type, ip_address, installation_path=installation_path)
        
        return jsonify({'return_code':1, 'message':'OK'}), 200

    @expose('/download/<agent_type>/<file_name>', methods=['GET'])
    @protect()
    def download_file(self, agent_type, file_name):

        #get file name from db
        realname = get_latest_file(agent_type, file_name)

        if not realname:
            return jsonify({'return_code':-1, 'message':'File not found'}), 404

        fm = S3FileManager()
        file_body = fm.get_file(realname)

        return send_file(BytesIO(file_body), download_name=file_name, as_attachment=True)
        
    @expose('/getRefreshToken/<agent_id>', methods=['GET'])
    @protect()
    def getRefreshToken(self, agent_id):

        refresh_token = create_refresh_token(g.user.id , expires_delta=timedelta(days=15))
        expiration_date = datetime.now() + timedelta(days=15)
        rtn , msg = update_expiration(agent_id, expiration_date, refresh_token)
        if rtn < 0:
            return jsonify({'return_code':rtn, 'message':msg, 'refresh_token':''}), 401
        return jsonify({'return_code':rtn, 'message':'OK', 'refresh_token':refresh_token}), 200

appbuilder.add_api(CommandApi)
appbuilder.add_api(AgentApi)
