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
from app.models.agent import AgCommandMaster, AgAgent, AgAgentGroup, AgCommandType
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
                      example: "NEWGEN.Read.http.m"
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

        command_type = db.session.query(AgCommandType).filter_by(command_type_id=command_type_id).first()
        if not command_type:
            return jsonify({'return_code': -2, 'message': f'Invalid command_type_id: {command_type_id}'}), 400

        broadcast_callback = data.get('broadcast_callback')
        target_agent_id = data.get('target_agent_id')
        target_agent_group_id = data.get('target_agent_group_id')

        if not (broadcast_callback or target_agent_id or target_agent_group_id):
            return jsonify({'return_code': -2, 'message': 'Target must be specified (broadcast_callback, target_agent_id, or target_agent_group_id)'}), 400

        parameters = data.get('parameters', '')
        if parameters is None:
            parameters = ''
        elif isinstance(parameters, (dict, list)):
            parameters = json.dumps(parameters)

        new_command_id = get_uuid()

        cmd_master = AgCommandMaster(
            command_id=new_command_id,
            ag_command_type=command_type,
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

    @expose('/extract_log', methods=['POST'])
    @protect(allow_browser_login=True)
    def extract_log(self):
        """특정 조건에 맞는 로그 추출 Command 등록
        ---
        post:
          summary: WAS 에러 로그 추출 명령 등록
          description: 특정 날짜, 시간, 키워드 등의 조건에 맞는 WAS 에러 로그를 추출하도록 CommandMaster를 생성하고 에이전트에 하달합니다.
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  required:
                    - host_id
                    - was_instance_id
                    - date
                    - time_from
                    - time_to
                  properties:
                    host_id:
                      type: string
                      description: 대상 서버 ID
                      example: "uok01a"
                    was_instance_id:
                      type: string
                      description: 대상 WAS 인스턴스 ID
                      example: "uok01a_servlet_engine1"
                    date:
                      type: string
                      description: 추출 기준 날짜 (yyyymmdd 형식)
                      example: "20260825"
                    time_from:
                      type: string
                      description: 추출 시작 시간 (hhmmss 형식)
                      example: "140439"
                    time_to:
                      type: string
                      description: 추출 종료 시간 (hhmmss 형식)
                      example: "150000"
                    file_name:
                      type: string
                      description: 대상 로그 파일명. (선택) 입력하지 않을 경우 시스템이 날짜에 맞춰 자동 생성합니다. 'file' 이라는 키로도 입력 가능.
                    keywords:
                      type: array
                      items:
                        type: string
                      description: 검색할 키워드 목록 (선택) 기본값은 ["Exception", "Fail"] 입니다.
                      example: ["Exception", "Fail", "Error"]
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
              description: 필수 파라미터 누락, 유효하지 않은 포맷 등 잘못된 요청
            500:
              description: 서버 내부 에러
        """
        try:
            data = json.loads(request.data) if request.data else request.json
        except Exception:
            return jsonify({'return_code': -1, 'message': 'Invalid JSON'}), 400

        if not data:
            return jsonify({'return_code': -1, 'message': 'Empty payload'}), 400

        host_id = data.get('host_id')
        was_instance_id = data.get('was_instance_id')
        date = data.get('date') # yyyymmdd
        time_from = data.get('time_from') # hhmmss
        time_to = data.get('time_to') # hhmmss
        file_name = data.get('file_name', data.get('file', ''))
        keywords = data.get('keywords', ["Exception", "Fail"])

        if not all([host_id, was_instance_id, date, time_from, time_to]):
            return jsonify({'return_code': -2, 'message': 'Missing required parameters (host_id, was_instance_id, date, time_from, time_to)'}), 400

        # 1. 파일명 생성 로직
        if not file_name:
            today_str = datetime.now().strftime("%Y%m%d")
            if date == today_str:
                file_name = f"/log/jeus/{was_instance_id}/JeusServer.log"
            else:
                file_name = f"/log/jeus/{was_instance_id}/JeusServer_{date}.log"
        
        # 2. 날짜 포맷 변환 (start, end)
        try:
            start = f"{date[:4]}.{date[4:6]}.{date[6:8]} {time_from[:2]}:{time_from[2:4]}:{time_from[4:6]}"
            end = f"{date[:4]}.{date[4:6]}.{date[6:8]} {time_to[:2]}:{time_to[2:4]}:{time_to[4:6]}"
        except IndexError:
            return jsonify({'return_code': -1, 'message': 'Invalid date or time format'}), 400

        # 3. Target Agent 찾기
        target_agent = None
        cand_agents = [
            f"{host_id}_jeus_J",
            f"{host_id}_webtob_J"
        ]
        
        for cand in cand_agents:
            agent = db.session.query(AgAgent).filter(AgAgent.agent_id == cand, AgAgent.approved_yn == 'YES').first()
            if agent:
                target_agent = agent
                break
                
        if not target_agent:
            agent = db.session.query(AgAgent).filter(AgAgent.agent_id.like(f"{host_id}_%_J"), AgAgent.approved_yn == 'YES').first()
            if agent:
                target_agent = agent

        if not target_agent:
            return jsonify({'return_code': -1, 'message': f'Approved agent not found for host: {host_id}'}), 400

        # 4. Command Type 검증
        command_type_id = "EXTRACT.LOG"
        command_type = db.session.query(AgCommandType).filter_by(command_type_id=command_type_id).first()
        if not command_type:
            return jsonify({'return_code': -2, 'message': f'Invalid command_type_id: {command_type_id}'}), 400

        # 5. Parameters (추가 파라미터 구성)
        parameters = {
            "file": file_name,
            "start": start,
            "end": end,
            "keywords": keywords,
            "dateRegex": "\\[(\\d{4}\\.\\d{2}\\.\\d{2} \\d{2}:\\d{2}:\\d{2})\\](?:\\s*\\[[^\\]]*\\]){1,2}",
            "abbreviatePrefix": "\tat "
        }
        
        new_command_id = get_uuid()

        cmd_master = AgCommandMaster(
            command_id=new_command_id,
            ag_command_type=command_type,
            periodic_type=PeriodicTypeEnum.IMMEDIATE,
            additional_params=json.dumps(parameters),
            publish_yn=YnEnum.YES,
            cancel_yn=YnEnum.NO,
            finished_yn=YnEnum.NO,
            command_sender=TargetToSendEnum.SERVER,
            result_receiver=TargetToSendEnum.SERVER
        )
        
        cmd_master.ag_agent.append(target_agent)

        try:
            db.session.add(cmd_master)
            db.session.commit()
            return jsonify({'return_code': 1, 'message': 'OK', 'command_id': new_command_id}), 201
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error creating CommandMaster EXTRACT.LOG: {str(e)}')
            return jsonify({'return_code': -1, 'message': 'Internal Server Error'}), 500

appbuilder.add_api(CommandMasterApi)
