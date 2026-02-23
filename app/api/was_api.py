from app import appbuilder, db
from flask import jsonify, request, render_template
from flask_appbuilder.api import BaseApi, ModelRestApi, expose, protect
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import has_access
from app.sqls.server import get_servers, add_server, update_server, delete_server
from app.sqls.was import get_next_old_was_text, get_next_old_web_text
from app.sqls.monitor import select_row
from app.models.was import MwServer
from app.dmlsForAgent import AutorunResult
import json

class MwServerApi(BaseApi):
    resource_name = 'mw_server'

    @expose('/list', methods=['GET'])
    @protect()
    def list(self):
        """List all servers or filter by host_id"""
        host_id = request.args.get('host_id')
        
        if host_id:
            server = get_servers(host_id)
            if not server:
                return jsonify({'message': f'Server {host_id} not found'}), 404
            return jsonify(self._serialize_server(server))
        
        servers = get_servers()
        return jsonify([self._serialize_server(s) for s in servers])

    @expose('/add', methods=['POST'])
    @protect()
    def add(self):
        """Create a new server"""
        try:
            data = json.loads(request.data)
        except Exception:
            return jsonify({'message': 'Invalid JSON'}), 400

        server, msg = add_server(data)
        if not server:
            return jsonify({'message': msg}), 400 if msg != "Internal Server Error" else 500
            
        return jsonify({'message': 'Created', 'id': server.id, 'host_id': server.host_id}), 201

    @expose('/edit/<host_id>', methods=['PUT'])
    @protect()
    def edit(self, host_id):
        """Update an existing server"""
        try:
            data = json.loads(request.data)
        except Exception:
            return jsonify({'message': 'Invalid JSON'}), 400

        server, msg = update_server(host_id, data)
        if not server:
            return jsonify({'message': msg}), 404 if "not found" in msg else 400
            
        return jsonify({'message': 'Updated', 'host_id': host_id}), 200

    @expose('/delete/<host_id>', methods=['DELETE'])
    @protect()
    def delete(self, host_id):
        """Delete a server"""
        success, msg = delete_server(host_id)
        if not success:
            return jsonify({'message': msg}), 404 if "not found" in msg else 500
            
        return jsonify({'message': 'Deleted', 'host_id': host_id}), 200

    def _serialize_server(self, server):
        return {
            'id': server.id,
            'host_id': server.host_id,
            'server_name': server.server_name,
            'landscape': server.landscape.name if server.landscape else None,
            'os_type': server.os_type.name if server.os_type else None,
            'encoding': server.encoding.name if server.encoding else None,
            'jdk_version': server.jdk_version,
            'ip_address': server.ip_address,
            'vip_address': server.vip_address,
            'running_type': server.running_type.name if server.running_type else None,
            'primary_host_id': server.primary_host_id,
            'dr_host_id': server.dr_host_id,
            'use_yn': server.use_yn.name if server.use_yn else None
        }

class MWConfiguration(BaseApi):

    resource_name = 'config'

    @expose('/httpm', methods=['POST'])
    @protect()
    def httpm_config(self, **kwargs):

        data = json.loads(request.data)

        if not data.get('content'):
            return jsonify({'return_code':-2,'message':'content must be included'}), 401
        elif not data.get('host_id'):
            return jsonify({'return_code':-2,'message':'host_id must be included'}), 401
    
        content   = data['content']
        host_id   = data['host_id']
        sys_user = data['sys_user'] if data.get('sys_user') else ''

        rtn, msg = AutorunResult()._update_httpm(host_id, content, sys_user=sys_user)
        db.session.commit()

        if rtn < 0:
            return jsonify({'return_code':rtn, 'msg':msg}), 400

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
        sys_user = data['sys_user'] if data.get('sys_user') else ''
        
        domain_info = dict(
            host_id = host_id,
            domain_id = domain_id,
            content = content,
            sys_user = sys_user,
            agent_id = '',
        )

        rtn, msg = AutorunResult.update_domain(domain_info)
        db.session.commit()

        if rtn < 0:
            return jsonify({'return_code':rtn, 'msg':msg}), 400

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

class MwDiff(BaseApi):

    route_base = '/diff'

    @expose('/was/<id>', methods=['GET'])
    @has_access
    def diff_was(self, id):

        row, _ = select_row('mw_was_change_history',{'id':id})
        title = f'{row.mw_was} updated at {row.create_on.strftime("%Y-%m-%d %H:%M:%S")}'

        old_domain, new_domain = get_next_old_was_text(id=id)

        return render_template('diff.html'\
            , title=title
            , text1=old_domain
            , text2=new_domain
            , base_template=appbuilder.base_template
            , appbuilder=appbuilder
            )

    @expose('/web/<id>', methods=['GET'])
    @has_access
    def diff_web(self, id):

        row, _ = select_row('mw_web_change_history',{'id':id})
        title = f'{row.mw_web} updated at {row.create_on.strftime("%Y-%m-%d %H:%M:%S")}'

        old_httpm, new_httpm = get_next_old_web_text(id=id)

        return render_template('diff.html'\
            , title=title
            , text1=old_httpm
            , text2=new_httpm
            , base_template=appbuilder.base_template
            , appbuilder=appbuilder
            )

class ServerModelApi(ModelRestApi):
    resource_name = 'Server'
    datamodel = SQLAInterface(MwServer)

appbuilder.add_api(MwServerApi)
appbuilder.add_api(MWConfiguration)
appbuilder.add_api(MwDiff)
appbuilder.add_api(ServerModelApi)
