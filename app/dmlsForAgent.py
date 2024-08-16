import logging
from app import db
from .dmlsForJeus import JeusDomain, JeusDomainFactory, OldJeusDomain, NewJeusDomain
from .dmlsForWebtob import WebtobHttpm, WebtobHttpmFactory, NewHttpm, httpmToDict
from app.sqls.was import getDomainIdAsPK, getWasInstanceId
from app.sqls.agent import updateResultStatus, updateWasStatus, getResult, getAutorunFunc\
    , sendCommandImmediately, getOrInsertCommandType, insertCommandMaster\
    , getCommandMaster
from app.sqls.monitor import update_rows, insert_row, select_row, select_rows
from app.models.common import get_date
from datetime import datetime, timedelta
from deepdiff import DeepDiff
import json
import xmltodict
import sys
import re

class AutorunResult:

    def __init__(self, result=None, result_id=None):
        if result!=None:
            self.result = result
        elif result_id!=None:
            self.result = getResult(result_id)
        else:
            self.result=None

    def getAutorunFunc(self):

        if self.result.ag_command_detail.command_class.name == 'DownloadFile':
            return None, None

        real_key_value1 = self._getRealKeyValue1(self.result.key_value1)

        return getAutorunFunc(self.result.command_id, real_key_value1)

    def _getRealKeyValue1(self, key_value1):

        real_key_value1 = key_value1

        n_list = key_value1.rsplit('.',1)

        if len(n_list) == 2 and len(n_list[1]) == 12:
            rec = getCommandMaster(n_list[1])
            if rec:
                real_key_value1 = n_list[0]

        return real_key_value1

    def callAutorunFunc(self):

        autorunFunc, autorunParam = self.getAutorunFunc()

        if not autorunFunc:
            return 0, 'No Autorun'

        try:
            func = getattr(self, autorunFunc)

            if autorunParam:
                rtn, msg = func(autorunParam, self.result.command_id)
            else:
                rtn, msg = func()

            code = 'COMPLITED' if rtn > 0 else 'NOCHANGE' if rtn==0 else 'ERROR'
            self.updateResultStatus(code, msg)
        except AttributeError as e:
            return -1, autorunFunc + ': Not Exists'
        except Exception as e:
            db.session.rollback()
            excType, excValue, traceback = sys.exc_info()
            logging.error(f'AutorunResult.callAutorunFunc Error : 1{excType} 2{excValue} 3{traceback}')
            self.updateResultStatus('ERROR', str(excValue))

        return 1, 'OK'

    def __get_domain_info(self):

        result = self.result

        file_name = result.key_value1
        file_path = result.key_value2

        content   = result.result_text
        host_id   = result.host_id.lower()
        agent_id  = result.agent_id

        if result.ag_command_detail.command_class.name == 'ExeAgentFunc':
            sys_user = ''
        else:
            sys_user = agent_id[agent_id.find('_')+1:agent_id.rfind('_')]

        #Getting domain id from file_path ex) /sw/jeus/domains/PPRM_Domain/config
        if file_name == 'domain.xml':
            real_domain_id = file_path[file_path.find('domains')+8:file_path.find('config')-1]

        elif file_name == 'JEUSMain.xml':
            fpl = file_path.split('/')
            real_domain_id = fpl[fpl.index('config')-1]

        domain_id = getDomainIdAsPK(host_id, real_domain_id)
        # 예외로직 : utc10t 두번째 jeusok 의 domain id를 jeusok2_dev로 고정
        if host_id == 'uok01a' and 'usropt01/jeus60/jeusok' in file_path:
            domain_id = 'jeusok2_dev'

        return dict(
            host_id = host_id,
            domain_id = domain_id,
            content = content,
            sys_user = sys_user,
            agent_id = agent_id,
        )

    def updateJeusDomain(self):
        domain_info = self.__get_domain_info()
        return AutorunResult.update_domain(domain_info)

    @classmethod
    def update_domain(cls, domain_info):

        doc        = xmltodict.parse(domain_info.content)
        json_type  = json.dumps(doc)
        dict2_type = json.loads(json_type)
        
        domain = dict2_type['domain'] if dict2_type.get('domain') else dict2_type['jeus-system'] if dict2_type.get('jeus-system') else None

        if not domain:
            return -1, 'domain item doesn\'t exist'

        rec, _ = select_row('mw_was',{'was_id':domain_info.domain_id})
        
        if rec and rec.was_object:

            diff = DeepDiff(rec.was_object, domain, ignore_order=True)

            #Not changed
            if not diff:
                return 0, 'Not changed'

            insert_dict = dict(
                mw_was_id      = rec.id,
                old_was_object = rec.was_object,
                changed_object = diff.to_json(),
                old_was_text   = rec.was_text,
            )

            insert_row('mw_was_change_history', insert_dict)
        
        fac = JeusDomainFactory()
        
        param = dict(
            domain_id = domain_info.domain_id,
            host_id   = domain_info.host_id,
            domain    = domain,
            raw_data  = domain_info.content,
            sys_user  = domain_info.sys_user,
            agent_id  = domain_info.agent_id,
        )

        if dict2_type.get('domain'):
            jeus = NewJeusDomain(**param)
        elif dict2_type.get('jeus-system'):
            jeus = OldJeusDomain(**param)

        rtn , _ = fac.jeus_domain(jeus)
        
        return rtn, ''

    def updateUrlRewrite(self):

        result = self.result
        
        filter_dict = dict(command_id=result.command_id)
        cmaster, _ = select_row('ag_command_master', filter_dict)

        urlrewrite_config = cmaster.additional_params

        update_dict = dict(
            urlrewrite_text = result.result_text
           ,urlrewrite_update_date = datetime.now()
        )

        host_id   = result.host_id.lower()

        filter_dict = dict(
            host_id           = host_id
           ,urlrewrite_config = urlrewrite_config
        )

        update_rows('mw_web_vhost', update_dict, filter_dict)

        return 1, ''

    def update_file_SSL_byAPI(self):

        result = self.result

        result_text   = result.result_text
        certi = json.loads(result_text)

        logging.info(f'certi : {certi}')

        ssl_certi = certi['certifile']

        notbefore, notafter = self._getSslDatetime(certi)

        update_dict = dict(
            notbefore = notbefore
           ,notafter  = notafter
           ,subject   = certi['subject']
           ,serial    = certi['serial']
           ,issuer    = certi['issuer']
           ,update_dt = datetime.now()
            )

        host_id   = result.host_id.lower()

        filter_dict = dict(
            host_id   = host_id
           ,ssl_certi = ssl_certi
        )

        return update_rows('mw_web_ssl', update_dict, filter_dict)

    def _getSslDatetime(self, certi):

        if 'GMT' in certi['notbefore']:
            notbefore = datetime.strptime(certi['notbefore'], "%a %b %d %H:%M:%S %Z %Y")\
                        + timedelta(hours=9)

            notafter  = datetime.strptime(certi['notafter'], "%a %b %d %H:%M:%S %Z %Y")\
                        + timedelta(hours=9)
        else:
            notbefore = datetime.strptime(certi['notbefore'], "%a %b %d %H:%M:%S KST %Y")
            notafter  = datetime.strptime(certi['notafter'], "%a %b %d %H:%M:%S KST %Y")

        return notbefore, notafter

    def updateConnectSSLByAPI(self):

        result = self.result

        result_text   = result.result_text
        result_dict = json.loads(result_text)
        certi = next( r for r in result_dict['certs'] if r['index']=="1")

        notbefore, notafter = self._getSslDatetime(certi)

        update_dict = dict(
            notbefore = notbefore
           ,notafter  = notafter
           ,subject   = certi['subject']
           ,serial    = certi['serial']
           ,issuer    = certi['issuer']
           ,update_dt = datetime.now()
            )

        certi_ca = next(( r for r in result_dict['certs'] if r['index']=="2"), None )

        if certi_ca:
            notbefore_ca, notafter_ca = self._getSslDatetime(certi_ca)
            update_dict.update(
                dict(
                    notbefore_ca = notbefore_ca
                   ,notafter_ca  = notafter_ca
                   ,subject_ca   = certi_ca['subject']
                   ,serial_ca    = certi_ca['serial']
                   ,issuer_ca    = certi_ca['issuer']
                )
            )

        host_id   = result.host_id.lower()
        domain, port = result_dict['domain'].split(':', 1)

        filter_dict = dict(
            host_id     = host_id
           ,domain_name = domain
           ,port        = port
        )

        return update_rows('mw_web_domain', update_dict, filter_dict)

    def updateConnectSSL(self):

        result = self.result

        content   = result.result_text
        host_id   = result.host_id.lower()

        ssl_dict = self._parseSSLInfo(content)

        if not ssl_dict.get('domain'):
            return -1, 'Domain doesn\'t exist'

        if ':' not in ssl_dict['domain']:
            return -1, 'Domain isn\'t valid'

        #if not ssl_dict.get('serial'):
        #    return -1, 'Serial doesn\'t exist'

        if not ssl_dict.get('notafter') or not ssl_dict['notafter']:
            update_dict = dict(
                subject   = 'Connection Failed'
               ,update_dt = datetime.now()
            )

            #return -1, 'NotAfter isn\'t valid'
        else:
            update_dict = dict(
                notbefore = ssl_dict['notbefore']
               ,notafter  = ssl_dict['notafter']
               ,subject   = ssl_dict['subject']
               ,serial    = ssl_dict['serial']
               ,issuer    = ssl_dict['issuer']
               ,update_dt = datetime.now()
            )

        domain, port = ssl_dict['domain'].split(':', 1)

        filter_dict = dict(
            host_id     = host_id
           ,domain_name = domain
           ,port        = port
        )

        return update_rows('mw_web_domain', update_dict, filter_dict)

    def updateFileSSL(self):

        result = self.result

        content   = result.result_text
        host_id   = result.host_id.lower()

        ssl_dict = self._parseSSLInfo(content)

        if not ssl_dict.get('file'):
            return -1, 'SSL file doesn\'t exist'

        if not ssl_dict.get('serial'):
            return -1, 'Serial doesn\'t exist'

        if not ssl_dict.get('notafter') or not ssl_dict['notafter']:
            return -1, 'NotAfter isn\'t valid'

        ssl_certi = ssl_dict['file']

        update_dict = dict(
            notbefore = ssl_dict['notbefore']
           ,notafter  = ssl_dict['notafter']
           ,subject   = ssl_dict['subject']
           ,serial    = ssl_dict['serial']
           ,issuer    = ssl_dict['issuer']
           ,update_dt = datetime.now()
        )

        filter_list = dict(
            host_id     = host_id
           ,ssl_certi   = ssl_certi
        )

        return update_rows('mw_web_ssl', update_dict, filter_dict)

    def _parseSSLInfo(self, content):

        item_names = ['file','domain','notbefore','notafter','subject','serial','issuer']
        rtn_dict = {}
        info_list = content.splitlines()

        for l in info_list:

            tlist = [ i.strip() for i in l.split('=',1) ]

            if len(tlist)==2 and tlist[0].lower() in item_names:

                if tlist[0].lower() in ['notbefore','notafter']:

                    try:
                        if 'GMT' in tlist[1]:
                            dt = datetime.strptime(tlist[1], '%b %d %H:%M:%S %Y %Z')\
                                + timedelta(hours=9)
                        else:
                            dt = datetime.strptime(tlist[1], '%b %d %H:%M:%S %Y %Z')

                    except ValueError:
                        dt = None

                    rtn_dict.update({tlist[0].lower():dt})
                else:
                    rtn_dict.update({tlist[0].lower():tlist[1]})

        return rtn_dict

    def update_httpm(self):

        result = self.result

        file_name = result.key_value1
        file_path = result.key_value2
        content   = result.result_text
        host_id   = result.host_id.lower()

        #내장 WEB서버 식별
        if 'webserver/config' in file_path:
            fpl = file_path.split('/')
            real_domain_id = fpl[fpl.index('webserver')-1]

            domain_id = getDomainIdAsPK(host_id, real_domain_id)
            # 예외로직 : utc10t 두번째 jeusok 의 domain id를 jeusok2_dev로 고정
            if host_id == 'uok01a' and 'usropt01/jeus60/jeusok' in file_path:
                domain_id = 'jeusok2_dev'
        else:
            domain_id = ''

        agent_id = result.agent_id

        if result.ag_command_detail.command_class.name == 'ExeAgentFunc':
            sys_user = ''
        else:
            sys_user = agent_id[agent_id.find('_')+1:agent_id.rfind('_')]

        return self._update_httpm(host_id, content, sys_user=sys_user\
                        , domain_id=domain_id, agent_id=agent_id)

    def _update_httpm(self, host_id, content, sys_user='', domain_id='', agent_id=''):

        httpm = httpmToDict(content)

        if not httpm['NODE'][0].get('JSVPORT'):
            httpm['NODE'][0]['JSVPORT'] = 0

        if httpm['NODE'][0].get('PORT'):
            tmp = httpm['NODE'][0]['PORT']
            port = int(tmp.split(',')[0])
        else:
            port = 0
            httpm['NODE'][0]['PORT'] = "0"

        rec, _ = select_row('mw_web',{'host_id':host_id,'port':port})

        if rec:
            diff = DeepDiff(rec.httpm_object, httpm, ignore_order=True)

            #Not changed
            if not diff:
                return 0, 'Not changed'

            insert_dict = dict(
                mw_web_id         = rec.id,
                old_httpm_object  = rec.httpm_object,
                changed_object    = diff.to_json(),
                old_web_text      = rec.web_text,
            )

            insert_row('mw_web_change_history', insert_dict)

        fac = WebtobHttpmFactory()
        
        httpm = NewHttpm(
            host_id, 
            httpm,
            raw_data  = content,
            sys_user  = sys_user, 
            domain_id = domain_id, 
            agent_id  = agent_id
        )
        
        rtn , _ = fac.webtobHttpm(httpm)
        return rtn, ''

    def updateWebMain(self):

        result = self.result

        file_name = result.key_value1
        file_path = result.key_value2

        content   = result.result_text
        host_id   = result.host_id.lower()

        fpl = file_path.split('/')
        real_domain_id = fpl[fpl.index('config')-1]

        domain_id = getDomainIdAsPK(host_id, real_domain_id)
        # 예외로직 : utc10t 두번째 jeusok 의 domain id를 jeusok2_dev로 고정
        if host_id == 'uok01a' and 'usropt01/jeus60/jeusok' in file_path:
            domain_id = 'jeusok2_dev'

        if file_path[-1:] in ['/','\\']:
            file_path = file_path[:-1]

        #예) '/usropt02/jeus/config/urt02a/urt02a_servlet_rehi2' => 'rehi2'
        engine_command_cand1 = file_path.split('_')[-1:][0]
        #예) '/usropt02/jeus/config/urt02a/urt02a_servlet_rehi2' => '2'
        engine_command_cand2 = file_path[-1:]
        
        was_instance_id = getWasInstanceId(host_id, domain_id, engine_command_cand1)
        if not was_instance_id:
            was_instance_id = getWasInstanceId(host_id, domain_id, engine_command_cand2)

        if not was_instance_id:
            return -1, 'was_instance_id doesn\'t exist'

        return self._updateWebMain(host_id, domain_id, was_instance_id, content)
        
    def _updateWebMain(self, host_id, domain_id, was_instance_id, content):

        doc        = xmltodict.parse(content)
        json_type  = json.dumps(doc)
        dict2_type = json.loads(json_type)
        
        domain = dict2_type['web-container']
        domain.update(name=was_instance_id)
        
        fac = JeusDomainFactory()
        jeusDomain = OldJeusDomain(domain_id, host_id, domain)
        rtn , _ = fac.jeus_web_connection(jeusDomain)
        
        return rtn, ''

    def readOutFile(self, command_type_id, command_id):
        rtn , _ = insertCommandMaster(command_type_id, [self.result.agent_id])
        return rtn, ''

    def readCIDOutFile(self, command_type_id, command_id):
        rtn , _ = insertCommandMaster(command_type_id, [self.result.agent_id], command_id)
        return rtn, ''

    def updateJeusLicenseInfo(self):

        result = self.result

        content   = result.result_text

        re_dict = self._parseJeusLicenseInfo(content)

        logging.info(f're_dict : {re_dict}')

        if not re_dict.get('domain'):
            return -1, 'No data found'

        update_dict = dict(
            license_cpu         = re_dict['cpu'] if re_dict.get('cpu') else 0
           ,license_edition     = re_dict['edition'] if re_dict.get('edition') else ''
           ,license_hostname    = re_dict['host-name'] if re_dict.get('host-name') else ''
           ,license_issue_date  = re_dict['issue-day'] if re_dict.get('issue-day') else None
           ,license_due_date    = re_dict['due-day'] if re_dict.get('due-day') else None
           ,license_text        = content
           ,license_update_date = get_date()
           ,version_info        = re_dict['version-info'] if re_dict.get('version-info') else None
        )

        filter_list = dict(
            was_id     = re_dict['domain']
        )

        return update_rows('mw_was', update_dict, filter_list)

    def _parseJeusLicenseInfo(self, content):

        item_names = ['domain','edition','issue-day','cpu','host-name','due-day']
        rtn_dict = {}
        info_list = content.splitlines()

        for line in info_list:

            l = line.strip('=')
            tlist = [ i.strip() for i in l.split(':',1) ]

            if len(tlist)==1 and len(l) > 0 and l[0].isdigit():
                rtn_dict.update({'version-info':l})

            elif len(tlist)==2 and tlist[0].lower() in item_names:

                if tlist[0].lower() in ['issue-day','due-day']:

                    try:
                        dt = datetime.strptime(tlist[1], '%Y/%m/%d')
                    except ValueError:
                        dt = None

                    rtn_dict.update({tlist[0].lower():dt})
                elif tlist[0].lower() == 'cpu':
                    if tlist[1] == 'unlimited':
                        rtn_dict.update({tlist[0].lower():0})
                    else:
                        rtn_dict.update({tlist[0].lower():int(tlist[1])})
                else:
                    rtn_dict.update({tlist[0].lower():tlist[1]})

        return rtn_dict

    def updateFilteredInfo(self):

        result = self.result

        content   = result.result_text

        re_dict = self._parseFilteredInfo(content)

        if not re_dict.get('domain'):
            return -1, 'No data found'

        update_dict = dict(
            filtered_text        = content
           ,filtered_update_date = get_date()
        )

        filter_list = dict(
            was_id     = re_dict['domain']
           ,application_home = re_dict['application_home']
        )

        return update_rows('mw_application', update_dict, filter_list)

    def _parseFilteredInfo(self, content):

        item_names = ['domain','application_home']
        rtn_dict = {}
        info_list = content.splitlines()

        for line in info_list:

            tlist = [ i.strip() for i in line.split(':',1) ]

            if len(tlist)==2 and tlist[0].lower() in item_names:

                rtn_dict.update({tlist[0].lower():tlist[1]})

        return rtn_dict

    def updateWebtobLicenseInfo(self):

        result = self.result

        content   = result.result_text

        re_dict = self._parseWebtobLicenseInfo(content)

        if not re_dict.get('host_id'):
            return -1, 'No data found'

        update_dict = dict(
            license_cpu         = re_dict['cpu'] if re_dict.get('cpu') else 0
           ,license_edition     = re_dict['edition'] if re_dict.get('edition') else ''
           ,license_hostname    = re_dict['license check by hostname'] if re_dict.get('license check by hostname') else ''
           ,license_issue_date  = re_dict['license issue date'] if re_dict.get('license issue date') else None
           ,license_text        = content
           ,license_update_date = get_date()
        )

        filter_list = dict(
            host_id  = re_dict['host_id']
           ,port     = re_dict['port']
        )

        return update_rows('mw_web', update_dict, filter_list)

    def _parseWebtobLicenseInfo(self, content):

        item_names = ['domain','edition','license issue date','license check by hostname']
        rtn_dict = {}
        info_list = content.splitlines()

        for l in info_list:

            tlist = [ i.strip() for i in l.split(':',1) ]

            if len(tlist)==2 and tlist[0].lower() in item_names:

                if tlist[0].lower() == 'license issue date':

                    try:
                        dt = datetime.strptime(tlist[1], '%Y/%m/%d')
                    except ValueError:
                        dt = None

                    rtn_dict.update({tlist[0].lower():dt})
                elif tlist[0] == 'domain':
                    host_id, port = tlist[1].split('__')
                    rtn_dict.update({'host_id':host_id, 'port':int(port)})
                else:
                    rtn_dict.update({tlist[0].lower():tlist[1]})
            elif 'CPU license' in l:
                cpu = re.findall(r'\d+', l)
                rtn_dict.update({'cpu':int(cpu[0])})

        return rtn_dict

    def updateWasStatus(self):

        result = self.result

        rtn, _ = updateWasStatus(result.key_value2, result.result_text, result.host_id)

        return rtn, ''

    def updateJeusProperties(self):

        result = self.result

        #혹시 한 jeus에 여러 domain이 설치된 경우도 있을 수 있어서
        was_ids = self._getWasId4JEUSHome(result.agent_id, result.key_value2)

        if not was_ids:
            return 0, 'WAS not found'

        update_dict = dict(
            jeus_properties_text = result.result_text
           ,jeus_properties_update_date = datetime.now()
        )

        for was_id in was_ids:

            filter_dict = dict(
                was_id           = was_id
            )

            update_rows('mw_was', update_dict, filter_dict)

        return 1, ''

    def updateWebtobMonitor(self):

        result = self.result

        row, _ = select_row('mw_web',{'agent_id':result.agent_id})
        
        if not row:
            return 0, 'WEB not found'

        dicts = self.__get_si(result.result_text, result.create_on.strftime('%Y.%m.%d %H:%M'))

        for r in dicts:
            srow, _ = select_row('mw_web_server',{'svr_id':r['svr_id'],'mw_web_id':row.id})

            if srow:
                srow.monitor_now = r

                tmp = dict()
                if srow.monitor_history:
                    tmp = srow.monitor_history
                else:
                    tmp = {'history':[]}

                tmp['history'].append(r)
                srow.monitor_history = tmp

        return 1, ''

    def __get_si(self, result, date):

        array_ = []
        
        for line in result.splitlines():
            if not line.strip():
                continue

            logging.info(f'line : {line}')
            ll = [ t for t in line.split(' ') if t and '(' not in t and ')' not in t]
            
            array_.append(
                dict(
                    svr_id = ll[1],
                    status = ll[2],
                    regs   = ll[3],
                    count  = ll[4],
                    cqcnt  = ll[5],
                    aqcnt  = ll[6],
                    qpcnt  = ll[7],
                    emcnt  = ll[8],
                    rscnt  = ll[9],
                    rbcnt  = ll[10],
                    date   = date,
                )
            )

        return array_

    def updateWebtobVersion(self):

        result = self.result

        row, _ = select_row('mw_web',{'agent_id':result.agent_id})
        
        if not row:
            return 0, 'WEB not found'

        row.version_info = result.result_text

        return 1, ''

    def _getWasId4JEUSHome(self, agent_id, jeusprop_location):

        filter_dict = dict(
            mapping_key = 'DOMAIN_HOME'
           ,agent_id    = agent_id
           ,string_to_replace = jeusprop_location
        )

        recs, _ = select_rows('ag_command_helper', filter_dict)

        if recs:
            return [ r.target_file_name for r in recs]

        filter_dict = dict(
            agent_id    = agent_id
        )

        recs, _ = select_rows('mw_was', filter_dict)
        
        if recs:
            return [ r.was_id for r in recs]

        return None

    def restartMWAgent(self):

        result = self.result

        if result.ag_command_detail.ag_agent.agent_sub_type != None:
            return -1, 'agent_sub_type is not defined.'

        _restartShell = {
            'WIN_JEUS8' :'run.agent.bat'
           ,'WIN_JEUS7' :'run.agent4j7.bat'
           ,'WIN_JEUS6' :'run.agent4j6.bat'
           ,'UNIX_JEUS6':'run.agent4j6.sh'
           ,'UNIX_JEUS8':'run.agent.sh'
        }

        agent_sub_type = result.ag_command_detail.ag_agent.agent_sub_type.name
        
        command_type_id = getOrInsertCommandType('ExeShell'
           ,target_file_name=_restartShell[agent_sub_type])

        rtn, _ = sendCommandImmediately(result.agent_id, command_type_id)

        return rtn, ''

    def updateResultStatus(self, code, message):

        update_dict = dict(
            result_status  = code
           ,complited_date = datetime.now()
           ,result_message = message
        )

        filter_dict = dict(id = self.result.id)

        update_rows('ag_result', update_dict, filter_dict)


