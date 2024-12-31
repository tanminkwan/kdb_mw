import requests
import json


#################################################################
url = 'http://127.0.0.1:5000'
#url = 'http://10.9.62.162:5000'

data =dict(password='1q2w3e4r!!',username='tiffanie',provider='db',refresh='true')

headers = {'Content-Type':'application/json;charset=utf-8'}
resp = requests.post(url+'/api/v1/security/login'\
    , data=json.dumps(data), headers=headers)

print('Get access token : ')
print(resp.json())
access_token = resp.json()['access_token']
#################################################################
#xml = 'domain_deaiaa11.xml'
#host_id = 'deaiaa11'
#domain_id = 'DEIM_Domain'

#xml = 'domain_phmpaa11.xml'
#host_id = 'phmpaa11'
#domain_id = 'PHMP_Domain'

#xml = 'domain_uhc57a_PRMS_Domain.xml'
#host_id = 'uhc57a'
#domain_id = 'PRMS_Domain'
#system_user = 'jeus'

#xml = 'domain_papmar11.xml'
#host_id = 'papmar11'
#domain_id = 'PAPM_Domain'

#xml = 'domain_itb.xml'
#host_id = 'pitbaa11'
#domain_id = 'PITB_Domain'

#xml = 'domain_mdm.xml'
#host_id = 'pmbpar11'
#domain_id = 'PMDM_Domain'

#xml = 'domain_piciaa11.xml'
#host_id = 'piciaa11'
#domain_id = 'PICI_Domain'

#xml = 'domain_pecmaa11.xml'
#host_id = 'pecmaa11'
#domain_id = 'PEKM_Domain'

#xml = 'domain_pecmaa21.xml'
#host_id = 'pecmaa21'
#domain_id = 'PECM_Domain'

#xml = 'domain_rdw.xml'
#host_id = 'prdwaa11'
#domain_id = 'PRDW_Domain'

#xml = 'domain_padwaa11.xml'
#host_id = 'padwaa11'
#domain_id = 'PADW_Domain'

xml = 'domain_pprmar11.xml'
host_id = 'pprmar11'
domain_id = 'PPMS_Domain'
system_user = 'jeus'

#xml = 'domain_pdqmar11.xml'
#host_id = 'pdqmar11'
#domain_id = 'PDQM_Domain'

#xml = 'domain_pismar11.xml'
#host_id = 'pismar11'
#domain_id = 'PISM_Domain'

#xml = 'domain_pmbpaw11.xml'
#host_id = 'pmbpaw11'
#domain_id = 'PMBP_Domain'

#xml = 'domain_pgweaa11.xml'
#host_id = 'pgweaa11'
#domain_id = 'PGWE_Domain'

##AS-IS
#xml = 'JEUSMain_urt02a.xml'
#host_id = 'urt02a'
#domain_id = 'jeus'
#system_user = 'jeus'

#xml = 'domain_pbiiar11.xml'
#host_id = 'pbiiar11'
#domain_id = 'PBII_Domain'

#xml = 'domain_pbiiar11.xml'
#host_id = 'pbiiar11'
#domain_id = 'PITT_Domain'

#xml = 'domain_pbpmaa11.xml'
#host_id = 'pbpmaa11'
#domain_id = 'PBPM_Domain'

#xml = 'domain_pumsar11.xml'
#host_id = 'pumsar11'
#domain_id = 'PPUS_Domain'

#xml = 'domain_pbdpar21.xml'
#host_id = 'pbdpar21'
#domain_id = 'PBDE_Domain'

#xml = 'domain_pessar11.xml'
#host_id = 'pessar11'
#domain_id = 'PBII2_Domain'

#xml = 'domain_piitpw11.xml'
#host_id = 'piitpw11'
#domain_id = 'PIIT_Domain'

#xml = 'domain_piccar21.xml'
#host_id = 'piccar21'
#domain_id = 'PCAM_Domain'

#xml = 'domain_piccar31.xml'
#host_id = 'piccar31'
#domain_id = 'PCAQ_Domain'

#xml = 'domain_pesscr21.xml'
#host_id = 'pesscr21'
#domain_id = 'PCAS_Domain'

#xml = 'domain_piccpr21.xml'
#host_id = 'piccpr21'
#domain_id = 'PCRS_Domain'

#xml = 'domain_peaiaa11.xml'
#host_id = 'peaiaa11'
#domain_id = 'PEIM_Domain'

#xml = 'domain_pewmcr11.xml'
#host_id = 'pewmcr11'
#domain_id = 'PWMM_Domain'

#xml = 'domain_picccr11.xml'
#host_id = 'picccr11'
#domain_id = 'PICC_Domain'

#xml = 'domain_pumscr11.xml'
#host_id = 'pumscr11'
#domain_id = 'PUMS_Domain'

#xml = 'domain_pwcmpw11.xml'
#host_id = 'pwcmpw11'
#domain_id = 'PWCM_Domain'

##AS-IS
#xml = 'JEUSMain_utc07a_ke.xml'
#host_id = 'utc07a'
#domain_id = 'jeuske'

##AS-IS
#xml = 'JEUSMain_utc07a_ex.xml'
#host_id = 'utc07a'
#domain_id = 'jeusex'

##AS-IS
#xml = 'JEUSMain_utc07a_kr.xml'
#host_id = 'utc07a'
#domain_id = 'jeuskr'

##AS-IS
#xml = 'JEUSMain_utc07a_lw.xml'
#host_id = 'utc07a'
#domain_id = 'jeuslw'

##AS-IS
#xml = 'JEUSMain_utc07a_pu.xml'
#host_id = 'utc07a'
#domain_id = 'jeuspu'

##AS-IS
#xml = 'JEUSMain_uea01e.xml'
#host_id = 'uea01e'
#domain_id = 'jeusea'

##AS-IS
#xml = 'JEUSMain_utc12y_jeusea.xml'
#host_id = 'utc12t'
#domain_id = 'jeusea_dev'

##AS-IS
#xml = 'JEUSMain_uhr75a_shr.xml'
#host_id = 'uhr75a'
#domain_id = 'jeushr'

##AS-IS
#xml = 'JEUSMain_uok05a.xml'
#host_id = 'uok05a'
#domain_id = 'jeusok_05'

fd = open(xml, 'r', encoding='utf-8')
content = fd.read()

data = dict(content=content, host_id=host_id, domain_id=domain_id, system_user=system_user)

headers = {'Content-Type':'application/json;charset=utf-8','Authorization':'Bearer '+access_token}
resp = requests.post(url+'/api/v1/config/jeusdomain'\
    , data=json.dumps(data) , headers=headers)

print(resp.json())