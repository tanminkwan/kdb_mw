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
from app.models.agent import AgCommandMaster, AgAgent, AgAgentGroup
from app.models.common import PeriodicTypeEnum, YnEnum, TargetToSendEnum, get_uuid

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

class CommandMasterApi(BaseApi):

    resource_name = 'command_master'

    @expose('/create', methods=['POST'])
    @protect()
    def create(self):
        """즉시 실행 가능한 CommandMaster 데이터를 생성합니다. (API Key 인증 지원)
        ---
        post:
          summary: CommandMaster 즉시 실행 명령 생성
          description: 외부 시스템에서 API Key를 사용하여 즉시 실행 가능한 명령어(CommandMaster)를 생성합니다.
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    command_type_id:
                      type: string
                      description: 실행할 명령어 타입 ID
                      example: "CMD_UPDATE_CONFIG"
                    broadcast_callback:
                      type: string
                      description: 브로드캐스트용 콜백 함수명 (선택)
                    target_agent_id:
                      type: array
                      items:
                        type: string
                      description: 대상 에이전트 ID 목록 (선택, 단일 문자열도 가능)
                    target_agent_group_id:
                      type: array
                      items:
                        type: string
                      description: 대상 에이전트 그룹 ID 목록 (선택, 단일 문자열도 가능)
                    parameters:
                      type: object
                      description: 명령어 실행 시 필요한 추가 파라미터 (JSON 객체 또는 문자열)
                      example: {"module": "nginx", "restart": true}
          responses:
            201:
              description: 생성 성공
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      return_code:
                        type: integer
                        example: 1
                      message:
                        type: string
                        example: "OK"
                      command_id:
                        type: string
                        description: 생성된 명령어의 UUID
            400:
              description: 필수 파라미터 누락 등 잘못된 요청
        """
        try:
            data = json.loads(request.data) if request.data else request.json
        except Exception:
            return jsonify({'return_code': -1, 'message': 'Invalid JSON'}), 400

        if not data:
            return jsonify({'return_code': -1, 'message': 'Empty payload'}), 400

        command_type_id = data.get('command_type_id')
        if not command_type_id:
            return jsonify({'return_code': -2, 'message': 'command_type_id is required'}), 400

        broadcast_callback = data.get('broadcast_callback')
        target_agent_id = data.get('target_agent_id')
        target_agent_group_id = data.get('target_agent_group_id')

        if not (broadcast_callback or target_agent_id or target_agent_group_id):
            return jsonify({'return_code': -2, 'message': 'Target must be specified (broadcast_callback, target_agent_id, or target_agent_group_id)'}), 400

        parameters = data.get('parameters')
        if isinstance(parameters, (dict, list)):
            parameters = json.dumps(parameters)

        new_command_id = get_uuid()

        cmd_master = AgCommandMaster(
            command_id=new_command_id,
            command_type_id=command_type_id,
            periodic_type=PeriodicTypeEnum.IMMEDIATE,
            additional_params=parameters,
            publish_yn=YnEnum.YES,
            cancel_yn=YnEnum.NO,
            finished_yn=YnEnum.NO,
            command_sender=TargetToSendEnum.SERVER,
            result_receiver=TargetToSendEnum.SERVER,
            broadcast_callback=broadcast_callback
        )

        if target_agent_id:
            agent_ids = [target_agent_id] if isinstance(target_agent_id, str) else target_agent_id
            agents = db.session.query(AgAgent).filter(AgAgent.agent_id.in_(agent_ids)).all()
            if agents:
                cmd_master.ag_agent.extend(agents)
                
        if target_agent_group_id:
            group_ids = [target_agent_group_id] if isinstance(target_agent_group_id, str) else target_agent_group_id
            groups = db.session.query(AgAgentGroup).filter(AgAgentGroup.agent_group_id.in_(group_ids)).all()
            if groups:
                cmd_master.ag_agent_group.extend(groups)

        try:
            db.session.add(cmd_master)
            db.session.commit()
            return jsonify({'return_code': 1, 'message': 'OK', 'command_id': new_command_id}), 201
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error creating CommandMaster: {str(e)}')
            return jsonify({'return_code': -1, 'message': 'Internal Server Error'}), 500

appbuilder.add_api(CommandMasterApi)
