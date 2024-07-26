from . import appbuilder, db
from flask import g
from sqlalchemy.sql import select, update, func
from sqlalchemy import null, text, or_, not_
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert, JSON
from .models import MwWasInstance, MwServer, MwWas, MwWeb, MwWaschangeHistory\
            , MwWebchangeHistory, MwWasWebtobConnector, MwWebServer\
            , MwDatasource, MwApplication, MwWebVhost, MwWasHttpListener\
            , MwWebDomain, MwWebReverseproxy
from .sqls_monitor import selectRow
import re

def getChangedWAS(create_on=None):

    recs = None

    if create_on:
        recs = db.session.query(MwWaschangeHistory)\
            .filter(MwWaschangeHistory.create_on>=create_on)\
            .order_by(MwWaschangeHistory.create_on.desc()).all()
    
    if recs:
        return recs
    else:
        return None 

def getChangedWEB(create_on=None):

    recs = None

    if create_on:
        recs = db.session.query(MwWebchangeHistory)\
            .filter(MwWebchangeHistory.create_on>=create_on)\
            .order_by(MwWebchangeHistory.create_on.desc()).all()
    
    if recs:
        return recs
    else:
        return None 

def getWasInstanceId(host_id, domain_id, engine_command):

    was_instance_rec = db.session.query(MwWasInstance)\
                    .filter(MwWasInstance.host_id==host_id
                        , MwWasInstance.was_id==domain_id
                        , MwWasInstance.engine_command.like('%'+engine_command+'%')).first()
    if was_instance_rec:
        return was_instance_rec.was_instance_id
    else:
        return None

def getHostId(ip_address):

    server_rec = db.session.query(MwServer)\
                    .filter(MwServer.ip_address==ip_address).first()
    if server_rec:
        return server_rec.host_id

    server_rec2 = db.session.query(MwServer)\
                    .filter(MwServer.vip_address.like('%'+ip_address+'%')).first()

    if server_rec2:
        return server_rec2.host_id

    return ip_address

def getDomainIdAsPK(host_id, real_domain_id, second=False):

    #차세대
    if real_domain_id.find('_Domain') >= 0:
        #if host_id in ['pessar11','desscr31']:
        #    domain_id = real_domain_id.replace('BII','BII2')
        #elif host_id in ['pewmcr11']:
        #    domain_id = real_domain_id.replace('PWMM','PEWM')
        #else:
        #    domain_id = real_domain_id
        
        domain_id = real_domain_id
    #ASIS
    else:
        
        landscape = getLandscape(host_id)

        #운영국외점포 분기
        if host_id in ['uok01a','uok02d']:
            real_domain_id = real_domain_id + '_A'
        elif host_id in ['uok03a','uok04d']:
            real_domain_id = real_domain_id + '_L'
        elif host_id in ['uok05a','uok06d']:
            real_domain_id = real_domain_id + '_N'
            
        if landscape == 'TEST' or real_domain_id == 'jeusei2':
            domain_id = real_domain_id + '_test'
        elif landscape == 'DEV':
            domain_id = real_domain_id + '_dev'
        else:
            domain_id = real_domain_id

    if second==True:
        domain_id += '2'

    return domain_id

def getLandscape(host_id):

    print('HH :',host_id)
    server_rec = db.session.query(MwServer)\
                    .filter(MwServer.host_id==host_id).first()
    if server_rec:
        return server_rec.landscape.name
    else:
        return None

def getWebRelationship(host_id, port):

    web_rec = db.session.query(MwWeb)\
                    .filter(MwWeb.host_id==host_id,MwWeb.port==port).first()

    if not web_rec or not web_rec.httpm_object:
        return None
    return _getWebRelationship(web_rec)

def _getWebRelationship(web_rec):

    mw_web_id = web_rec.id
    obj       = web_rec.httpm_object
    host_id   = web_rec.host_id

    operators = dict()
    links = dict()
    line_cnt = 0
    line_height = 32

    vhosts = []
    operators.update({"VHOST":{"top":20, "left":20, "properties":{"title":'VHOST 정보',"inputs": {},"outputs":{}}}})
    
    if obj['NODE'][0].get('PORT'):
        port = int(obj['NODE'][0]['PORT'])

    if obj.get('VHOST'):
        vhosts = obj['VHOST']
        for vhost in vhosts:
            vname = vhost['NAME']
            hostname = vhost['HOSTNAME'][0]
            port = vhost['PORT']

            if vhost.get('SSLFLAG') and vhost['SSLFLAG'].upper()=='Y':
                protocol = 'https://'
            else:
                protocol = 'http://'

            operators["VHOST"]["properties"]["outputs"]\
                .update({vname:{"label":protocol+hostname+':'+str(vhost['PORT'])}})

    #else:
    #    operators.update({"VHOST":{"top":20, "left":20, "properties":{"title":'NODE 정보',"inputs": {},"outputs":{}}}})
    vhosts.append({'HOSTNAME':host_id,'PORT':obj['NODE'][0]['PORT'],'NAME':'NODE'})
    operators["VHOST"]["properties"]["outputs"]\
            .update({'node':{"label":'http://(IP_Address):'+obj['NODE'][0]['PORT']}})
    #if obj.get('SSL'):
    #    operators["VHOST"]["properties"]["outputs"]\
    #        .update({'node_ssl':{"label":'https://(IP_Address):'+obj['NODE'][0]['PORT']}})

    top = 20
    left = 430

    #REVERSE PROXY
    rproxys = []
    if obj.get('REVERSE_PROXY'):

        rproxys = obj['REVERSE_PROXY']
        operators.update({'RPROXY':{"top":top, "left":left, "properties":{"title":'Reverse Proxy',"inputs": {},"outputs":{}}}})
        operators.update({'RPROXY_OUT':{"top":top, "left":left + 350, "properties":{"title":'Reverse Proxy Target',"inputs": {},"outputs":{}}}})

        for rp in rproxys:

            line_cnt += 1

            operators['RPROXY']["properties"]["inputs"]\
                .update({rp['NAME']:{"label":rp['PATHPREFIX']}})
            operators['RPROXY']["properties"]["outputs"]\
                .update({rp['NAME']+'_':{"label":'>'}})

            if rp.get('PROXYSSLFLAG'):
                uri = 'https://'
            else:
                uri = 'http://'

            operators['RPROXY_OUT']["properties"]["inputs"]\
                .update({rp['NAME']+'_T':{"label":uri + rp['SERVERADDRESS'] + rp['SERVERPATHPREFIX']}})

            link_key = 'RP_'+rp['NAME']
            links.update({link_key:
                dict(fromOperator='RPROXY'
                    ,fromConnector=rp['NAME']+'_'
                    ,toOperator='RPROXY_OUT'
                    ,toConnector=rp['NAME']+'_T'
                    ,color='#b93b8f'
                    )
            })

            if rp.get('VHOSTNAME'):

                for vname in rp['VHOSTNAME']:
                    link_key = 'RP_'+rp['NAME']+'__'+vname
                    links.update({link_key:
                        dict(fromOperator='VHOST'
                            ,fromConnector=vname
                            ,toOperator='RPROXY'
                            ,toConnector=rp['NAME']
                            ,color='#b93b8f'
                            )
                    })


    #SERVER
    svrgroups = []

    if obj.get('SVRGROUP'):
        svrgroups = obj['SVRGROUP']

    #URI
    uris = []

    jsvs = set()
    jsvmultis = []

    if obj.get('URI'):

        uris = obj['URI']

        for uri in uris:
            if not operators.get('URI_'+uri['SVRTYPE']):
                top += line_cnt * line_height
                left += 25
                operators.update({'URI_'+uri['SVRTYPE']:{"top":top, "left":left, "properties":{"title":'URI_'+uri['SVRTYPE'],"inputs": {},"outputs":{}}}})
            
            line_cnt += 1

            operators['URI_'+uri['SVRTYPE']]["properties"]["inputs"]\
                .update({uri['NAME']:{"label":uri['URI']}})

            if uri['SVRTYPE']=='JSV' and uri.get('SVRNAME'):
                operators['URI_'+uri['SVRTYPE']]["properties"]["outputs"]\
                    .update({uri['NAME']+'_':{"label":'>'}})

                jsvs.add(uri['SVRNAME'])
                jsvmultis.append((uri['NAME']+'_',[uri['SVRNAME']]))

            elif uri['SVRTYPE']=='JSV' and uri.get('LBSVGNAME'):

                #lbs, lbb = next((sg['LBSERVERS'], sg['LBBACKUP'] for sg in svrgroups if sg['NAME']==uri['LBSVGNAME']),('',''))
                sgt = next((sg['LBSERVERS'], sg['LBBACKUP']) for sg in svrgroups if sg['NAME']==uri['LBSVGNAME'])

                jsvs.add(sgt[0])
                jsvs.add(sgt[1])
                jsvmultis.append((uri['NAME']+'_',[sgt[0],sgt[1]]))

                operators['URI_'+uri['SVRTYPE']]["properties"]["outputs"]\
                    .update({uri['NAME']+'_':{"label":'>'}})

            if uri.get('VHOSTNAME'):
                for vname in uri['VHOSTNAME']:
                    link_key = 'URI_'+uri['NAME']+'__'+vname
                    links.update({link_key:
                        dict(fromOperator='VHOST'
                            ,fromConnector=vname
                            ,toOperator='URI_'+uri['SVRTYPE']
                            ,toConnector=uri['NAME']
                            ,color='#CD5C5C'
                            )
                        })
            else:
                link_key = 'URI_'+uri['NAME']+'__node'
                links.update({link_key:
                    dict(fromOperator='VHOST'
                        ,fromConnector='node'
                        ,toOperator='URI_'+uri['SVRTYPE']
                        ,toConnector=uri['NAME']
                        ,color='#CD5C5C'
                        )
                    })

                """
                if obj.get('SSL'):
                    link_key = 'URI_'+uri['NAME']+'__node_ssl'
                    links.update({link_key:
                        dict(fromOperator='VHOST'
                            ,fromConnector='node_ssl'
                            ,toOperator='URI_'+uri['SVRTYPE']
                            ,toConnector=uri['NAME']
                            ,color='#CD5C5C'
                            )
                    })
                """

    print('HHH 15 :',jsvs)

    jsvl = list(jsvs)

    if jsvl:
        ttop = top

        operators.update({'JSV_SERVER':{"top":ttop, "left":left + 350, "properties":{"title":'JSV Servers',"inputs": {},"outputs":{}}}})

        for js in jsvs:
            operators['JSV_SERVER']["properties"]["inputs"]\
                .update({js:{"label":js}})
        
        for js in jsvs:
            operators['JSV_SERVER']["properties"]["outputs"]\
                .update({'_'+js:{"label":js}})

        for j in jsvmultis:
            for svr in j[1]:

                link_key = j[0]+'_'+svr
                print('TT 1:',link_key)
                links.update({link_key:
                    dict(fromOperator='URI_JSV'
                        ,fromConnector=j[0]
                        ,toOperator='JSV_SERVER'
                        ,toConnector=svr
                        ,color='#b93b8f'
                    )
                })

        web_server_recs = db.session.query(MwWebServer)\
                    .filter(MwWebServer.mw_web_id==mw_web_id
                            ,MwWebServer.svr_id.in_(jsvl)).all()

        was_servers = []

        print('jsvmultis : ', jsvmultis)
        for wr in web_server_recs:        
            for was in wr.mw_was_webtobconnector:
                was_server = was.was_id + '_' + was.mw_was_instance.host_id
                if  was_server not in was_servers:
                    was_servers.append(was_server)
                    operators.update({was_server:{"top":ttop, "left":left + 700, "properties":{"title":was_server,"inputs": {},"outputs":{}}}})
                    ttop = ttop + 450
        
                operators[was_server]["properties"]["inputs"]\
                    .update({was.was_instance_id+'__'+wr.svr_id:{"label":was.was_instance_id+':'+wr.svr_id}})

                link_key = was_server+'_'+was.was_instance_id+'__'+wr.svr_id
                links.update({link_key:
                    dict(fromOperator='JSV_SERVER'
                        ,fromConnector='_'+wr.svr_id
                        ,toOperator=was_server
                        ,toConnector=was.was_instance_id+'__'+wr.svr_id
                        ,color='#b93b8f'
                    )
                })

    top += line_cnt * line_height
    left = 20

    #TCP Gateway
    if obj['NODE'][0].get('TCPGW'):
        operators.update({"TCPGW":{"top":top, "left":left, "properties":{"title":'TCP Gateway',"inputs": {},"outputs":{}}}})
        operators.update({"TCPGW_T":{"top":top, "left":left + 350, "properties":{"title":'TCP Gateway Target',"inputs": {},"outputs":{}}}})

        for tg in obj['TCPGW']:

            port = ''
            if tg.get('PORT'):
                port = tg['PORT']
            elif tg.get('LISTEN'):
                port = tg['LISTEN'].split(':')[1]

            operators["TCPGW"]["properties"]["outputs"]\
                .update({tg['NAME']:{"label":'Listen Port:'+port}})
            
            operators["TCPGW_T"]["properties"]["inputs"]\
                .update({tg['NAME']+'_T':{"label":tg['SERVERADDRESS']}})

            link_key = 'TCPGW_'+tg['NAME']
            links.update({link_key:
                dict(fromOperator='TCPGW'
                    ,fromConnector=tg['NAME']
                    ,toOperator='TCPGW_T'
                    ,toConnector=tg['NAME']+'_T'
                    ,color='#b93b8f'
                    )
            })

    json = {'operators':operators, 'links':links}
    print('HH1:',json)
    return json

def getRealWebHostId(web_host_id, host_id):

    if web_host_id in ['localhost','127.0.0.1','<domain-socket>']:
        real_host_id = host_id
    elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", web_host_id):
        real_host_id = getHostId(web_host_id)
    else:
        real_host_id = web_host_id

    return real_host_id

def getRProxyServers(host_id, port):

    row, _ = selectRow('mw_server',{'host_id':host_id})

    if not row:
        return None
    
    ips = [row.ip_address]
    if row.vip_address:
        ips = ips + [ x.strip() for x in row.vip_address.split(',')]

    rp_recs = db.session.query(MwWebReverseproxy)\
             .filter(MwWebReverseproxy.target_ip_address.in_(ips)
                    ,MwWebReverseproxy.target_port==port).all()
                    
    print('rp_recs :', rp_recs)
    return rp_recs

def getWebServers(webconn_rec):

    real_host_id = getRealWebHostId(webconn_rec.web_host_id, webconn_rec.mw_was_instance.host_id)
    
    if webconn_rec.web_host_id == '<domain-socket>':
        web_recs = db.session.query(MwWebServer)\
                    .filter( MwWebServer.svr_id==webconn_rec.jsv_id)\
                    .join(MwWeb)\
                    .filter(MwWeb.host_id==real_host_id
                            ,MwWeb.web_home==webconn_rec.web_home).all()
    elif webconn_rec.disable_pipe!=None and webconn_rec.disable_pipe.name == 'NO':
        web_recs = db.session.query(MwWebServer)\
                    .filter( MwWebServer.svr_id==webconn_rec.jsv_id)\
                    .join(MwWeb)\
                    .filter(MwWeb.host_id==real_host_id
                            ,MwWeb.dependent_was_id==webconn_rec.was_id).all()
    else:
        web_recs = db.session.query(MwWebServer)\
                    .filter( MwWebServer.svr_id==webconn_rec.jsv_id)\
                    .join(MwWeb)\
                    .filter(MwWeb.host_id==real_host_id
                            ,MwWeb.jsv_port==webconn_rec.jsv_port).all()

    return web_recs

def getWasRelationship(was_id):

    was_rec = db.session.query(MwWas)\
                    .filter(MwWas.was_id==was_id).first()
    
    newgeneration_yn = 'YES'
    if was_rec and was_rec.newgeneration_yn:
        newgeneration_yn = was_rec.newgeneration_yn.value
    else:
        return None 
    
    was_instance_recs = db.session.query(MwWasInstance)\
                    .filter(MwWasInstance.was_id==was_id,MwWasInstance.use_yn=='YES')\
                    .order_by(MwWasInstance.host_id.asc()).order_by(MwWasInstance.was_instance_id.asc()).all()

    operators = dict()
    links = dict()
    webs = set()

    operators.update({"DATABASE":{"top":20, "left":20, "properties":{"title":'DatabaseSource',"inputs": {},"outputs":{}}}})

    datasource_recs = db.session.query(MwDatasource)\
                    .filter(MwDatasource.was_id==was_id).all()

    for d_r in datasource_recs:

        db_user_id = '' if d_r.db_user_id==None else d_r.db_user_id
        db_server_name = '' if d_r.db_server_name==None else d_r.db_server_name
        db_server_port = '' if d_r.db_server_port==None else str(d_r.db_server_port)
        db_dbms_id = '' if d_r.db_dbms_id==None else d_r.db_dbms_id
        #if newgeneration_yn == 'YES':
            #label = d_r.datasource_id+':'+d_r.db_jndi_id
            #label = db_user_id+'@'+db_server_name+':'+db_server_port+'/'+db_dbms_id
        #else:
            #label = d_r.db_jndi_id+','+db_dbms_id
            #label = db_user_id+'@'+db_server_name+':'+db_server_port+'/'+db_dbms_id

        label = db_user_id+'@'+db_server_name+'/'+db_dbms_id
        label = label.replace('-vip','')
        operators["DATABASE"]["properties"]["outputs"].update({d_r.datasource_id:{"label":label}})        

    operators.update({"APPLICATION":{"top":450, "left":20, "properties":{"title":'Application',"inputs": {},"outputs":{}}}})

    application_recs = db.session.query(MwApplication)\
                    .filter(MwApplication.was_id==was_id).all()

    for a_r in application_recs:
        lable = a_r.application_id+':'+('~'+a_r.application_home[-22:] if len(a_r.application_home)>22 else a_r.application_home)
        operators["APPLICATION"]["properties"]["outputs"].update({a_r.application_id:{"label":lable}})        


    host_id = ""

    top = -180
    left = 430

    idx = -1
    colors = ['#008000','#c19a6b','#954535','#347c17','#b93b8f']

    for r in was_instance_recs:

        if host_id != r.host_id:
            top += 250
            operator_key = r.host_id + '_' + was_id
            operators.update({operator_key:{"top":top, "left":left, "properties":{"title":'WAS_'+r.host_id,"inputs": {},"outputs":{}}}})
            host_id = r.host_id
            idx += 1
        
        was_httpListener_rec = db.session.query(MwWasHttpListener)\
                    .filter( MwWasHttpListener.was_id==was_id\
                            ,MwWasHttpListener.was_instance_id==r.was_instance_id\
                            ,MwWasHttpListener.webconnection_id!='ADMIN-HTTP')\
                    .first()

        if was_httpListener_rec:
            label = '[http:'+str(was_httpListener_rec.listen_port)+'('+str(was_httpListener_rec.max_thread_pool_count)+')]'+r.was_instance_id

            rproxy_recs = getRProxyServers(host_id, was_httpListener_rec.listen_port)

            if rproxy_recs:

                for rproxy_rec in rproxy_recs:

                    real_host_id = rproxy_rec.mw_web.host_id
                    port = rproxy_rec.mw_web.port

                    toOperator = real_host_id + '_' + str(port)
                    print('rp toOperator : ',toOperator)
                    link_key = r.was_instance_id+'_'+ real_host_id + '_' + str(port) +'_'+rproxy_rec.reverseproxy_id
                    links.update({link_key:
                            dict(fromOperator=operator_key
                                ,fromConnector=r.was_instance_id
                                ,toOperator=toOperator
                                ,toConnector=rproxy_rec.reverseproxy_id
                                ,color='#17202A'
                                )
                            })

                    webs.add((real_host_id, port))

        else:
            label = r.was_instance_id

        operators[operator_key]["properties"]["outputs"].update({r.was_instance_id:{"label":label}})
        operators[operator_key]["properties"]["inputs"].update({r.was_instance_id+'_':{"label":'>'}})

        for d_r in r.mw_datasource:
            link_key = r.was_instance_id+'_'+d_r.datasource_id
            links.update({link_key:
                        dict(fromOperator='DATABASE'
                            ,fromConnector=d_r.datasource_id
                            ,toOperator=operator_key
                            ,toConnector=r.was_instance_id+'_'
                            ,color='#CD5C5C'
                            )
                        })

        for a_r in r.mw_application:
            link_key = r.was_instance_id+'_'+a_r.application_id
            links.update({link_key:
                        dict(fromOperator='APPLICATION'
                            ,fromConnector=a_r.application_id
                            ,toOperator=operator_key
                            ,toConnector=r.was_instance_id+'_'
                            ,color='#6495ED'
                            )
                        })

        was_webtobconnector_recs = db.session.query(MwWasWebtobConnector)\
                    .filter(MwWasWebtobConnector.was_id==was_id, MwWasWebtobConnector.was_instance_id==r.was_instance_id)\
                    .order_by(MwWasWebtobConnector.jsv_id.asc())\
                    .all()

        w_add_label = []

        for c_r in was_webtobconnector_recs:
            
            link_key = r.was_instance_id+'_'+c_r.webconnection_id

            w_add_label.append(str(c_r.thread_pool_count))

            web_recs = getWebServers(c_r)

            if web_recs:

                web_rec = web_recs[0]

                real_host_id = web_rec.mw_web.host_id
                port = web_rec.mw_web.port

                toOperator = real_host_id + '_' + str(port)
                links.update({link_key:
                        dict(fromOperator=operator_key
                            ,fromConnector=r.was_instance_id
                            ,toOperator=toOperator
                            ,toConnector=c_r.jsv_id
                            ,color=colors[idx]
                            )
                        })

                webs.add((real_host_id, port))

        if w_add_label:
            t_label = label + '(' + ','.join(w_add_label) + ')'
            operators[operator_key]["properties"]["outputs"].update({r.was_instance_id:{"label":t_label}})

    top = -180
    left = 810

    for w_r in sorted(webs):

        wc_r = db.session.query(MwWeb)\
                .filter(MwWeb.host_id==w_r[0], MwWeb.port==w_r[1]).first()

        top += 250
        operator_key = wc_r.host_id + '_' + str(wc_r.port)
        operators.update({operator_key:{"top":top, "left":left, "properties":{"title":'WEB_'+wc_r.host_id+'_'+str(wc_r.port),"inputs": {},"outputs":{}}}})

        was_webserver_recs = db.session.query(MwWebServer)\
                    .filter(MwWebServer.mw_web_id==wc_r.id)\
                    .order_by(MwWebServer.svr_id.asc())\
                    .all()

        for wcc_r in was_webserver_recs:
            operators[operator_key]["properties"]["outputs"].update({wcc_r.svr_id + '_':{"label":">"}})
            operators[operator_key]["properties"]["inputs"].update({wcc_r.svr_id:{"label":wcc_r.svr_id+"("+ str(wcc_r.max_proc_count) +")"}})

        was_rproxy_recs = db.session.query(MwWebReverseproxy)\
                    .filter(MwWebReverseproxy.mw_web_id==wc_r.id)\
                    .order_by(MwWebReverseproxy.reverseproxy_id.asc())\
                    .all()

        for wrp_r in was_rproxy_recs:
            operators[operator_key]["properties"]["outputs"].update({wrp_r.reverseproxy_id + '_':{"label":">"}})
            operators[operator_key]["properties"]["inputs"].update({wrp_r.reverseproxy_id:\
                    {"label":wrp_r.target_ip_address + ':' + str(wrp_r.target_port) + wrp_r.target_context_path+"("+ str(wrp_r.max_connection_count) +")"}})

        was_webvhost_recs = db.session.query(MwWebVhost)\
                    .filter(MwWebVhost.mw_web_id==wc_r.id)\
                    .order_by(MwWebVhost.vhost_id.asc())\
                    .all()

        if was_webvhost_recs:
            vOperator = 'VHOST_' + wc_r.host_id + '_' + str(wc_r.port)
            operators.update({vOperator:{"top":top, "left":1140, "properties":{"title":'VHost_'+w_r[0],"inputs": {},"outputs":{}}}})

            for wv_r in was_webvhost_recs:
                operators[vOperator]["properties"]["inputs"].update({wv_r.vhost_id:{"label":wv_r.vhost_id+'('+wv_r.domain_name+':'+ wv_r.web_ports+')'}})

                for s_r in wv_r.mw_web_server:
                    link_key = wv_r.vhost_id+'_'+s_r.svr_id+'_'+wc_r.host_id
                    links.update({link_key:
                    dict(fromOperator =wc_r.host_id + '_' + str(wc_r.port)
                        ,fromConnector=s_r.svr_id + '_'
                        ,toOperator   =vOperator
                        ,toConnector  =wv_r.vhost_id
                        ,color='#800080'
                        )
                    })

                for r_r in wv_r.mw_web_reverseproxy:
                    link_key = wv_r.vhost_id+'_'+r_r.reverseproxy_id+'_'+wc_r.host_id
                    links.update({link_key:
                    dict(fromOperator =wc_r.host_id + '_' + str(wc_r.port)
                        ,fromConnector=r_r.reverseproxy_id + '_'
                        ,toOperator   =vOperator
                        ,toConnector  =wv_r.vhost_id
                        ,color='#17202A'
                        )
                    })

    #print('operators :', operators)
    #print('links :', links)
    json = {'operators':operators, 'links':links}
    return json
