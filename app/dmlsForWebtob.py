from abc import ABC, abstractmethod
import io
import re
from flask import g
from . import appbuilder, db
from datetime import datetime
from sqlalchemy import select, null, text
from sqlalchemy.dialects.postgresql import insert, JSON
from app.models.was import MwServer, MwWas, MwWasInstance, MwWeb, MwWebVhost, MwWasHttpListener\
    , MwWasWebtobConnector, MwWebReverseproxy, MwDatasource, MwApplication, MwWebUri, MwWebServer
from app.sqls.was import getLandscape
from app.sqls.batch import createDomainNameInfo, createSslInfo

class WebtobHttpm(ABC):

    def __init__(self, host_id, httpm, sys_user="", domain_id="", agent_id=""):
        self.host_id   = host_id
        self.port      = 0
        self.httpm     = httpm
        self.sys_user = sys_user
        self.agent_id  = agent_id
        self.landscape     = ''
        self.dependent_was_id = domain_id
        self.node      = {}
        self.ssl       = []
        self.proxy_ssl = []
        self.vhosts    = []
        self.servers   = []
        self.server_groups = []
        self.reverse_proxy = []
        self.uris      = []
        self.logging   = []
        self.errordocument = []
        self.ext       = []
        self.tcpgw     = []
        self.mw_web_id = None
        
        self._setSubGroup()

    @abstractmethod
    def _setSubGroup(self):
        
        self.node      = self.httpm['NODE'][0]
        self.ssl       = self.httpm['SSL'] if self.httpm.get('SSL') else []
        self.proxy_ssl = self.httpm['PROXY_SSL'] if self.httpm.get('PROXY_SSL') else []
        self.vhosts    = self.httpm['VHOST'] if self.httpm.get('VHOST') else []
        self.servers   = self.httpm['SERVER'] if self.httpm.get('SERVER') else []
        self.server_groups = self.httpm['SVRGROUP']\
                             if self.httpm.get('SVRGROUP') else []
        self.reverse_proxy = self.httpm['REVERSE_PROXY']\
                             if self.httpm.get('REVERSE_PROXY') else []
        self.uris      = self.httpm['URI'] if self.httpm.get('URI') else []
        self.logging   = self.httpm['LOGGING'] if self.httpm.get('LOGGING') else []
        self.errordocument = self.httpm['ERRORDOCUMENT']\
                             if self.httpm.get('ERRORDOCUMENT') else []
        self.ext       = self.httpm['EXT'] if self.httpm.get('EXT') else []
        self.tcpgw     = self.httpm['TCPGW'] if self.httpm.get('TCPGW') else []        

    def upsertWebtobHttpm(self):

        # 
        self.landscape = getLandscape(self.host_id)

        # Upsert mw_web
        _, insert_dict, update_dict = self.__getDictOfWeb()

        stmt = insert(MwWeb).values(insert_dict)    
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=['host_id', 'port'],
            set_=update_dict
        ).returning(MwWeb.id)
        rtn = db.session.execute(do_update_stmt)

        self.mw_web_id = next(rec[0] for rec in rtn)
        print('HH self.mw_web_id :',self.mw_web_id)

        # Upsert mw_web_server
        _, insert_array, update_array \
            = self.__getArrayDictOfWebServer()

        for insert_dict, update_dict in zip(insert_array, update_array):

            stmt = insert(MwWebServer).values(insert_dict)    
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['mw_web_id', 'svr_id'],
                set_=update_dict
            )
            db.session.execute(do_update_stmt)

        # Upsert mw_web_uri
        _, insert_array, update_array \
            = self.__getArrayDictOfWebUri()

        for insert_dict, update_dict in zip(insert_array, update_array):

            stmt = insert(MwWebUri).values(insert_dict)    
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['mw_web_id', 'uri_id'],
                set_=update_dict
            )
            db.session.execute(do_update_stmt)

        # Upsert mw_web_reverseproxy
        _, insert_array, update_array \
            = self.__getArrayDictOfWebReverseproxy()

        for insert_dict, update_dict in zip(insert_array, update_array):

            stmt = insert(MwWebReverseproxy).values(insert_dict)    
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['mw_web_id', 'reverseproxy_id'],
                set_=update_dict
            )
            db.session.execute(do_update_stmt)

        # Upsert mw_web_vhost
        _, insert_array, update_array \
            = self.__getArrayDictOfWebVhost()

        for insert_dict, update_dict in zip(insert_array, update_array):

            stmt = insert(MwWebVhost).values(insert_dict)    
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['mw_web_id', 'vhost_id'],
                set_=update_dict
            )
            db.session.execute(do_update_stmt)

        # insert/delete assoc_webserver_vhost
        self.__updateWebserver_Vhost()

        # insert/delete assoc_webserver_vhost
        self.__updateWeburi_Webserver()

        # insert/delete assoc_weburi_vhost
        self.__updateWeburi_Vhost()

        # insert/delete assoc_webreverseproxy_vhost
        self.__updateWebreverseproxy_Vhost()

        # insert/update MwWebSsl
        self.__updateSslInfo()

        # insert/update MwWebDomain
        self.__updateDomainNameInfo()

        # Commit
        #db.session.commit()
        return 1, {'result':'OK'}

    def __getDictOfWeb(self):

        update_dict, port = self._getDataOfWeb()

        insert_dict = update_dict.copy()
        insert_dict.update(
            host_id = self.host_id,
            port    = port
            )

        return 1, insert_dict, update_dict

    @abstractmethod
    def _getDataOfWeb(self):

        self.port = int(self.node['PORT'].split(',')[0])

        if self.node.get('LOGGING'):
            #print(self.logging)
            acc_dir = next((c['FILENAME'] for c in self.logging if self.node['LOGGING']==c['NAME']), null())
        else:
            acc_dir = null()

        update_dict = dict(
            jsv_port       = self.node['JSVPORT'],
            node_name      = self.node['NAME'],
            web_home       = self.node['WEBTOBDIR'] \
                            if self.node.get('WEBTOBDIR') else null(),
            doc_dir       = self.node['DOCROOT'] \
                            if self.node.get('DOCROOT') else null(),
            hth_count      = self.node['HTH'] \
                            if self.node.get('HTH') else null(),
            service_port   = self.node['PORT'] \
                            if self.node.get('PORT') else null(),
            landscape      = self.landscape,
            acc_dir        = acc_dir,
            ssl_object     = self.ssl ,
            proxy_ssl_object     = self.proxy_ssl ,
            logging_object       = self.logging ,
            errordocument_object = self.errordocument ,
            ext_object           = self.ext ,
            tcpgw_object         = self.tcpgw ,
            httpm_object         = self.httpm ,
            agent_id             = self.agent_id,
            user_id              = g.user.username,
            create_on            = datetime.now()
        )

        if self.sys_user:
            update_dict['sys_user'] = self.sys_user

        if self.dependent_was_id:
            update_dict['dependent_was_id'] = self.dependent_was_id
            update_dict['built_type'] = 'Internal'

        return update_dict, self.port

    """
    def __getTag(self):

        tag = 'WEB-' + self.host_id + '-' + str(self.port) + '-'\
             + (self.sys_user if self.sys_user else 'NOUSERID')
        tag_id = insertResourceTag('mw_web', tag)
        return tag_id
    """
    def __getArrayDictOfWebServer(self):

        update_array = []
        insert_array = []
        update_dict = {}
        insert_dict = {}
        
        for server in self.servers:

            update_dict, svr_id = self._getDataOfWebServer(server)

            insert_dict = update_dict.copy()
            insert_dict.update(
                        mw_web_id = self.mw_web_id,
                        svr_id    = svr_id
                        )

            update_array.append(update_dict)
            insert_array.append(insert_dict)        

        return 1, insert_array, update_array

    @abstractmethod
    def _getDataOfWebServer(self, server):

        svr_id = server['NAME']

        if server.get('REQUESTLEVELPING'):
            request_level_ping_yn = 'YES' if server['REQUESTLEVELPING'] in ['y','Y']\
                                    else 'NO'
        else:
            request_level_ping_yn = null()

        svr_type = next( sg['SVRTYPE'] for sg in self.server_groups if sg['NAME']==server['SVGNAME']).upper()

        update_dict = dict(
            max_proc_count  = server['MAXPROC'] if server.get('MAXPROC') else null(),
            min_proc_count  = server['MINPROC'] if server.get('MINPROC') else null(),
            svr_type        = svr_type,
            request_level_ping_yn = request_level_ping_yn,
            user_id         = g.user.username,
            create_on       = datetime.now()
        )

        return update_dict, svr_id

    def __getArrayDictOfWebUri(self):

        update_array = []
        insert_array = []
        update_dict = {}
        insert_dict = {}
        
        for uri in self.uris:

            update_dict, uri_id = self._getDataOfWebUri(uri)

            insert_dict = update_dict.copy()
            insert_dict.update(
                        mw_web_id = self.mw_web_id,
                        uri_id    = uri_id
                        )

            update_array.append(update_dict)
            insert_array.append(insert_dict)        

        return 1, insert_array, update_array

    @abstractmethod
    def _getDataOfWebUri(self, uri):

        uri_id = uri['NAME']

        update_dict = dict(
            svr_type        = uri['SVRTYPE'] if uri.get('SVRTYPE') else null(),
            uri             = uri['URI'],
            user_id         = g.user.username,
            create_on       = datetime.now()
        )

        return update_dict, uri_id

    def __getArrayDictOfWebReverseproxy(self):

        update_array = []
        insert_array = []
        update_dict = {}
        insert_dict = {}
        
        for rp in self.reverse_proxy:

            update_dict, reverseproxy_id = self._getDataOfWebReverseproxy(rp)

            insert_dict = update_dict.copy()
            insert_dict.update(
                        mw_web_id       = self.mw_web_id,
                        reverseproxy_id = reverseproxy_id
                        )

            update_array.append(update_dict)
            insert_array.append(insert_dict)        

        return 1, insert_array, update_array

    @abstractmethod
    def _getDataOfWebReverseproxy(self, rp):

        reverseproxy_id = rp['NAME']

        if rp.get('PROXYSSLFLAG'):
            ssl_yn = 'YES' if rp['PROXYSSLFLAG'] in ['y','Y'] else 'NO'
        else:
            ssl_yn = 'NO'

        update_dict = dict(
            context_path      = rp['PATHPREFIX'],
            target_ip_address = rp['SERVERADDRESS'].split(':')[0]\
                             if rp['SERVERADDRESS'].find(':') else rp['SERVERADDRESS'],
            target_port       = rp['SERVERADDRESS'].split(':')[1]\
                             if rp['SERVERADDRESS'].find(':') else null(),
            target_context_path  = rp['SERVERPATHPREFIX'],
            max_connection_count = rp['MAXWEBSOCKETCONNECTIONS']\
                             if rp.get('MAXWEBSOCKETCONNECTIONS') else null(),
            ssl_yn          = ssl_yn,
            user_id         = g.user.username,
            create_on       = datetime.now()
        )

        return update_dict, reverseproxy_id

    def __getArrayDictOfWebVhost(self):

        update_array = []
        insert_array = []
        update_dict  = {}
        insert_dict  = {}
        
        for vhost in self.vhosts:

            #print(vhost)
            update_dict, vhost_id = self._getDataOfWebVhost(vhost)

            insert_dict = update_dict.copy()
            insert_dict.update(
                        mw_web_id = self.mw_web_id,
                        vhost_id = vhost_id
                        )

            update_array.append(update_dict)
            insert_array.append(insert_dict)        

        return 1, insert_array, update_array

    @abstractmethod
    def _getDataOfWebVhost(self, vhost):

        vhost_id = vhost['NAME']

        if vhost.get('SSLFLAG'):
            ssl_yn = 'YES' if vhost['SSLFLAG'] in ['y','Y'] else 'NO'
            ssl_name = vhost['SSLNAME'] if vhost['SSLFLAG'] in ['y','Y'] else null()
        else:
            ssl_yn = 'NO'
            ssl_name = null()


        if vhost.get('URLREWRITE'):
            urlrewrite_yn = 'YES' if vhost['URLREWRITE'] in ['y','Y'] else 'NO'
            urlrewrite_config = vhost['URLREWRITECONFIG']

            if '${WEBTOBDIR}' in urlrewrite_config:
                urlrewrite_config.replace('${WEBTOBDIR}', self.node['WEBTOBDIR'])
    
        else:
            urlrewrite_yn = 'NO'
            urlrewrite_config = null()

        if vhost.get('LOGGING'):
            acc_dir = next( c['FILENAME'] for c in self.logging if vhost['LOGGING']==c['NAME'])
        else:
            acc_dir = null()

        #uri_object = []
        #[ uri_object.append(u) for u in self.uris if vhost_id in u['VHOSTNAME']]

        update_dict = dict(
            web_ports    = vhost['PORT'] if vhost.get('PORT') else null(),
            domain_name = ','.join(vhost['HOSTNAME']) if vhost.get('HOSTNAME') else null(),
            host_alias  = ','.join(vhost['HOSTALIAS']) if vhost.get('HOSTALIAS') else null(),
            doc_dir     = vhost['DOCROOT'] if vhost.get('DOCROOT') else null(),
            acc_dir     = acc_dir,
            ssl_yn      = ssl_yn,
            ssl_name    = ssl_name,
            urlrewrite_yn = urlrewrite_yn,
            urlrewrite_config = urlrewrite_config,
            #uri_object  = uri_object,
            user_id     = g.user.username,
            create_on   = datetime.now()
        )

        return update_dict, vhost_id

    def __updateWebserver_Vhost(self):

        for vhost in self.vhosts:

            svr_ids, vhost_id\
                 = self._getDataOfWebserver_Vhost(vhost)

            if not svr_ids:
                continue

            vhost_rec = db.session.query(MwWebVhost)\
                    .filter(MwWebVhost.mw_web_id==self.mw_web_id\
                        , MwWebVhost.vhost_id==vhost_id).first()

            server_recs = db.session.query(MwWebServer)\
                    .filter(MwWebServer.mw_web_id==self.mw_web_id\
                        , MwWebServer.svr_id.in_(svr_ids)).all()

            vhost_rec.mw_web_server = server_recs

        return 1

    @abstractmethod
    def _getDataOfWebserver_Vhost(self, vhost):

        svgs = []    
        [ svgs.append(g['NAME']) for g in self.server_groups\
                 if g.get('VHOSTNAME') and vhost['NAME'] in g['VHOSTNAME']]
        
        if not svgs:
            return [], ""

        svr_ids = [ s['NAME'] for s in self.servers if s['SVGNAME'] in svgs ]

        #print('jsv ids :', svr_ids)
        vhost_id = vhost['NAME']

        return svr_ids, vhost_id

    def __updateWeburi_Webserver(self):

        for uri in self.uris:

            svr_ids = []
            if uri.get('LBSVGNAME'):
                svr_ids = [s['NAME'] for s in self.servers if s.get('SVGNAME') and s['SVGNAME'] == uri['LBSVGNAME']]
            elif uri.get('SVRNAME'):
                svr_ids = [uri['SVRNAME']]
            else:
                continue

            uri_rec = db.session.query(MwWebUri)\
                    .filter(MwWebUri.mw_web_id==self.mw_web_id\
                        , MwWebUri.uri_id==uri['NAME']).first()

            webserver_recs = db.session.query(MwWebServer)\
                    .filter(MwWebServer.mw_web_id==self.mw_web_id\
                        , MwWebServer.svr_id.in_(svr_ids)).all()

            uri_rec.mw_web_server = webserver_recs

        return 1

    def __updateWeburi_Vhost(self):

        for vhost in self.vhosts:

            uri_ids, vhost_id\
                 = self._getDataOfWeburi_Vhost(vhost)

            if not uri_ids:
                continue

            vhost_rec = db.session.query(MwWebVhost)\
                    .filter(MwWebVhost.mw_web_id==self.mw_web_id\
                        , MwWebVhost.vhost_id==vhost_id).first()

            uri_recs = db.session.query(MwWebUri)\
                    .filter(MwWebUri.mw_web_id==self.mw_web_id\
                        , MwWebUri.uri_id.in_(uri_ids)).all()

            vhost_rec.mw_web_uri = uri_recs

        return 1

    @abstractmethod
    def _getDataOfWeburi_Vhost(self, vhost):

        vhost_id = vhost['NAME']
        uri_ids = [ u['NAME'] for u in self.uris\
                 if u.get('VHOSTNAME') and vhost_id in u['VHOSTNAME']]

        return uri_ids, vhost_id

    def __updateSslInfo(self):

        print('HHH __updateSslInfo')
        webInfo = {'host_id':self.host_id, 'port':self.port}

        createSslInfo(webInfo)

        return 1


    def __updateDomainNameInfo(self):

        webInfo = {'host_id':self.host_id, 'port':self.port}

        createDomainNameInfo(webInfo)

        return 1


    def __updateWebreverseproxy_Vhost(self):

        for vhost in self.vhosts:

            reverseproxy_ids, vhost_id\
                 = self._getDataOfWebreverseproxy_Vhost(vhost)

            if not reverseproxy_ids:
                continue

            vhost_rec = db.session.query(MwWebVhost)\
                    .filter(MwWebVhost.mw_web_id==self.mw_web_id\
                        , MwWebVhost.vhost_id==vhost_id).first()

            reverseproxy_recs = db.session.query(MwWebReverseproxy)\
                    .filter(MwWebReverseproxy.mw_web_id==self.mw_web_id\
                        , MwWebReverseproxy.reverseproxy_id.in_(reverseproxy_ids)).all()

            vhost_rec.mw_web_reverseproxy = reverseproxy_recs

        return 1

    @abstractmethod
    def _getDataOfWebreverseproxy_Vhost(self, vhost):

        vhost_id = vhost['NAME']
        reverseproxy_ids = [ u['NAME'] for u in self.reverse_proxy if vhost_id in u['VHOSTNAME']]

        return reverseproxy_ids, vhost_id

#차세대 Jeus Domain Configuration
class NewHttpm(WebtobHttpm):

    #Overided
    def _setSubGroup(self):
        return super()._setSubGroup()

    #Overided
    def _getDataOfWeb(self):
        return super()._getDataOfWeb()

    #Overided
    def _getDataOfWebServer(self, server):
        return super()._getDataOfWebServer(server)

    #Overided
    def _getDataOfWebVhost(self, vhost):
        return super()._getDataOfWebVhost(vhost)

    #Overided
    def _getDataOfWebserver_Vhost(self, vhost):
        return super()._getDataOfWebserver_Vhost(vhost)

    #Overided
    def _getDataOfWebUri(self, uri):
        return super()._getDataOfWebUri(uri)

    #Overided
    def _getDataOfWeburi_Vhost(self, vhost):
        return super()._getDataOfWeburi_Vhost(vhost)

    #Overided
    def _getDataOfWebReverseproxy(self, rp):
        return super()._getDataOfWebReverseproxy(rp)

    #Overided
    def _getDataOfWebreverseproxy_Vhost(self, vhost):
        return super()._getDataOfWebreverseproxy_Vhost(vhost)

#유지 Jeus Domain Configuration 
class OldHttpm(WebtobHttpm):

    #Overided
    def _setSubGroup(self):
        return super()._setSubGroup()

    #Overided
    def _getDataOfWeb(self):
        return super()._getDataOfWeb()

    #Overided
    def _getDataOfWebServer(self, server):
        return super()._getDataOfWebServer(server)

    #Overided
    def _getDataOfWebVhost(self, vhost):
        return super()._getDataOfWebVhost(vhost)

    #Overided
    def _getDataOfWebserver_Vhost(self, vhost):
        return super()._getDataOfWebserver_Vhost(vhost)

    #Overided
    def _getDataOfWebUri(self, uri):
        return super()._getDataOfWebUri(uri)

    #Overided
    def _getDataOfWeburi_Vhost(self, vhost):
        return super()._getDataOfWeburi_Vhost(vhost)

    #Overided
    def _getDataOfWebReverseproxy(self, rp):
        return super()._getDataOfWebReverseproxy(rp)

    #Overided
    def _getDataOfWebreverseproxy_Vhost(self, vhost):
        return super()._getDataOfWebreverseproxy_Vhost(vhost)

class WebtobHttpmFactory:
    def webtobHttpm(self, h):
        return h.upsertWebtobHttpm()

def httpmToDict(content):

    category = ''
    category_new = ''
    item = ''
    item_dict = dict()
    category_list = []
    all_dict = dict()

    content = content.replace('\\\n', '')
    f = content.split('\n')

    for line in f:
        
        print('line:',line)
        if line.strip() in ('', '\\n', '*DOMAIN', 'KDB'):
            continue

        if line.startswith('*'):
            if category:
                if item:
                    item_dict['NAME'] = item
                    category_list.append(item_dict)
                all_dict.update({category:category_list})
            item_dict = dict()
            category_list = []
            category = line[1:].rstrip()
            item = ''
            continue
        elif line.lstrip().startswith('#'):
            continue		

        if line.find('#') >= 0:
            line = line[:line.find('#')] #Remove Comments

        if line[0] not in (' ','\t'):
            if item and item_dict:
                item_dict['NAME'] = item
                category_list.append(item_dict)
            item_dict = dict()

            ll = line.split()
            item = ll[0]
            if len(ll) > 1:
                line = ''.join(ll[1:])
            else:
                continue
        
        line = line.strip().rstrip(',')
        qline = re.findall(r'(["].*?["])',line)		
        for q in qline:
            qq = q.replace(',','^').replace('=','#').replace('"','')            
            line = line.replace(q,qq)
        linelist = line.split(',')

        dic = dict()
        for ll in linelist:
            ll = ll.strip()
            lld = ll.split('=')
            value = lld[1].replace('#','=').replace('^',',').replace('\t','').strip()
            value_l = value.split(',')
            value_l = [ v.strip() for v in value_l]
            item_u = lld[0].upper().strip()
            if item_u in ['VHOSTNAME','HOSTNAME','HOSTALIAS']:
                dic.update({item_u:value_l})
            else:
                dic.update({item_u:value})

        line_dict = dic
        item_dict.update(line_dict)

    item_dict['NAME'] = item
    category_list.append(item_dict)
    all_dict.update({category:category_list})

#    print(all_dict)
    return all_dict
