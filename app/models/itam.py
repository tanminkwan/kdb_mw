from flask_appbuilder import Model
from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
from .common import get_user

class ItWas(Model):
    __tablename__ = "it_was"
    
    config_id          = Column(String(50), primary_key=True, nullable=False, comment='구성번호')
    config_name        = Column(String(500), comment='구성명')
    host_id            = Column(String(200), comment='설치호스트명')
    biz_system         = Column(String(500), comment='업무시스템')
    biz_team           = Column(String(200), comment='업무팀')
    run_env            = Column(String(100), comment='운용환경')
    config_status      = Column(String(100), comment='구성상태')
    install_user       = Column(String(100), comment='설치계정명')
    was_version        = Column(String(100), comment='WAS버전')
    jdk_version        = Column(String(100), comment='JDK버전')
    os_type            = Column(String(100), comment='OS종류')
    os_ver             = Column(String(100), comment='OS버전')
    service_ip         = Column(String(100), comment='서비스IP')
    gw_ip              = Column(String(100), comment='OS대표IP(GW기준)')
    web_share_type     = Column(String(100), comment='WEB공유구분')
    server_loc         = Column(String(200), comment='WAS서버위치')
    os_kernel          = Column(String(200), comment='OS커널')
    cpu_core           = Column(String(100), comment='CPU(Core)')
    mem_gb             = Column(String(100), comment='MEM(GB)')
    hw_name            = Column(String(200), comment='하드웨어네임')
    hw_group           = Column(String(200), comment='하드웨어그룹')
    dept_team          = Column(String(200), comment='담당팀')
    kdb_p_mngr         = Column(String(100), comment='KDB담당자(정)')
    kdb_s_mngr         = Column(String(100), comment='KDB담당자(부)')
    ito_p_mngr         = Column(String(100), comment='ITO담당자(정)')
    ito_s_mngr         = Column(String(100), comment='ITO담당자(부)')

    user_id            = Column(String(50), default=get_user, nullable=False)
    create_on          = Column(DateTime(), default=datetime.now, nullable=False)    

    def __repr__(self):
        return str(self.config_name) if self.config_name else str(self.config_id)

class ItWeb(Model):
    __tablename__ = "it_web"
    
    config_id          = Column(String(50), primary_key=True, nullable=False, comment='구성번호')
    config_name        = Column(String(500), comment='구성명')
    host_id            = Column(String(200), comment='설치호스트명')
    biz_system         = Column(String(500), comment='업무시스템')
    biz_team           = Column(String(200), comment='업무팀')
    gw_ip              = Column(String(100), comment='OS대표IP(GW기준)')
    service_ip         = Column(String(100), comment='서비스IP')
    run_env            = Column(String(100), comment='운용환경')
    config_status      = Column(String(100), comment='구성상태')
    install_user       = Column(String(100), comment='설치계정명')
    webtob_version     = Column(String(100), comment='Webtob버전')
    os_type            = Column(String(100), comment='OS종류')
    os_ver             = Column(String(100), comment='OS버전')
    node_port          = Column(String(50), comment='노드포트')
    ssl_yn             = Column(String(50), comment='SSL사용여부')
    ev_cert_yn         = Column(String(50), comment='EV인증서여부')
    server_loc         = Column(String(200), comment='WEB서버위치')
    os_kernel          = Column(String(200), comment='OS커널')
    cpu_core           = Column(String(100), comment='CPU(Core)')
    mem_gb             = Column(String(100), comment='MEM(GB)')
    hw_name            = Column(String(200), comment='하드웨어네임')
    hw_group           = Column(String(200), comment='하드웨어그룹')
    dept_team          = Column(String(200), comment='담당팀')
    kdb_p_mngr         = Column(String(100), comment='KDB담당자(정)')
    kdb_s_mngr         = Column(String(100), comment='KDB담당자(부)')
    ito_p_mngr         = Column(String(100), comment='ITO담당자(정)')
    ito_s_mngr         = Column(String(100), comment='ITO담당자(부)')

    user_id            = Column(String(50), default=get_user, nullable=False)
    create_on          = Column(DateTime(), default=datetime.now, nullable=False)    

    def __repr__(self):
        return str(self.config_name) if self.config_name else str(self.config_id)
