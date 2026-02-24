from flask import g, request, redirect, flash, url_for
from flask_wtf.csrf import generate_csrf
from flask_appbuilder import ModelView, BaseView, expose, has_access
from flask_appbuilder.models.sqla.interface import SQLAInterface
from .common import get_mw_user
import pandas as pd
from app import appbuilder, db
from app.models.itam import ItWas, ItWeb
import logging

log = logging.getLogger(__name__)

class ItWasModelView(ModelView):
    datamodel = SQLAInterface(ItWas)
    
    list_title = "IT WAS 구성정보"
    add_title = "IT WAS 구성정보 추가"
    edit_title = "IT WAS 구성정보 수정"
    show_title = "IT WAS 구성정보 상세"
    
    list_columns = [
        'config_id', 'config_name', 'host_id', 'biz_system', 'run_env', 
        'config_status', 'was_version', 'service_ip'
    ]
    
    label_columns = {
        'config_id': '구성번호',
        'config_name': '구성명',
        'host_id': '호스트ID',
        'biz_system': '업무시스템',
        'biz_team': '업무팀',
        'run_env': '운용환경',
        'config_status': '구성상태',
        'install_user': '설치계정',
        'was_version': 'WAS버전',
        'jdk_version': 'JDK버전',
        'os_type': 'OS종류',
        'os_ver': 'OS버전',
        'service_ip': '서비스IP',
        'gw_ip': 'OS대표IP(GW)',
        'web_share_type': 'WEB공유구분',
        'server_loc': '서버위치',
        'os_kernel': 'OS커널',
        'cpu_core': 'CPU(Core)',
        'mem_gb': 'MEM(GB)',
        'hw_name': 'H/W명',
        'hw_group': 'H/W그룹',
        'dept_team': '담당팀',
        'kdb_p_mngr': 'KDB담당자(정)',
        'kdb_s_mngr': 'KDB담당자(부)',
        'ito_p_mngr': 'ITO담당자(정)',
        'ito_s_mngr': 'ITO담당자(부)',
        'create_on': '생성일시'
    }

class ItWebModelView(ModelView):
    datamodel = SQLAInterface(ItWeb)
    
    list_title = "IT WEB 구성정보"
    add_title = "IT WEB 구성정보 추가"
    edit_title = "IT WEB 구성정보 수정"
    show_title = "IT WEB 구성정보 상세"
    
    list_columns = [
        'config_id', 'config_name', 'host_id', 'biz_system', 'run_env', 
        'config_status', 'webtob_version', 'service_ip'
    ]
    
    label_columns = {
        'config_id': '구성번호',
        'config_name': '구성명',
        'host_id': '호스트ID',
        'biz_system': '업무시스템',
        'biz_team': '업무팀',
        'gw_ip': 'OS대표IP(GW)',
        'service_ip': '서비스IP',
        'run_env': '운용환경',
        'config_status': '구성상태',
        'install_user': '설치계정',
        'webtob_version': 'Webtob버전',
        'os_type': 'OS종류',
        'os_ver': 'OS버전',
        'node_port': '노드포트',
        'ssl_yn': 'SSL사용여부',
        'ev_cert_yn': 'EV인증서여부',
        'server_loc': '서버위치',
        'os_kernel': 'OS커널',
        'cpu_core': 'CPU(Core)',
        'mem_gb': 'MEM(GB)',
        'hw_name': 'H/W명',
        'hw_group': 'H/W그룹',
        'dept_team': '담당팀',
        'kdb_p_mngr': 'KDB담당자(정)',
        'kdb_s_mngr': 'KDB담당자(부)',
        'ito_p_mngr': 'ITO담당자(정)',
        'ito_s_mngr': 'ITO담당자(부)',
        'create_on': '생성일시'
    }

class ItExcelImportView(BaseView):
    route_base = "/it_import"
    default_view = "upload"
    
    @expose("/upload", methods=['GET', 'POST'])
    @has_access
    def upload(self):
        if request.method == 'POST':
            file = request.files.get('file')
            import_type = request.form.get('type') # 'was' or 'web'
            
            if not file or file.filename == '':
                flash("파일을 선택해주세요.", "danger")
                return redirect(url_for(".upload"))
            
            try:
                df = pd.read_excel(file)
                # Normalize column names (remove newlines, spaces)
                df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
                
                if import_type == 'was':
                    self.import_was(df)
                elif import_type == 'web':
                    self.import_web(df)
                else:
                    flash("잘못된 요청입니다.", "danger")
                    return redirect(url_for(".upload"))
                
                db.session.commit()
                flash(f"{import_type.upper()} 데이터 임포트 완료", "success")
            except Exception as e:
                db.session.rollback()
                log.error(f"Excel import error: {str(e)}")
                flash(f"임포트 실패: {str(e)}", "danger")
                
            return redirect(url_for(".upload"))
            
        return self.render_template("itam_upload.html", csrf_token=generate_csrf())

    def import_was(self, df):
        mapping = {
            '구성번호': 'config_id',
            '구성명': 'config_name',
            '설치호스트명': 'host_id',
            '업무시스템': 'biz_system',
            '업무팀': 'biz_team',
            '운용환경': 'run_env',
            '구성상태': 'config_status',
            '설치계정명': 'install_user',
            'WAS버전': 'was_version',
            'JDK버전': 'jdk_version',
            'OS종류': 'os_type',
            'OS버전': 'os_ver',
            '서비스IP': 'service_ip',
            'OS대표IP (GW기준)': 'gw_ip',
            'WEB공유구분': 'web_share_type',
            'WAS서버위치': 'server_loc',
            'OS커널': 'os_kernel',
            'CPU (Core)': 'cpu_core',
            'MEM (GB)': 'mem_gb',
            '하드웨어네임': 'hw_name',
            '하드웨어그룹': 'hw_group',
            '담당팀': 'dept_team',
            'KDB담당자(정)': 'kdb_p_mngr',
            'KDB담당자(부)': 'kdb_s_mngr',
            'ITO담당자(정)': 'ito_p_mngr',
            'ITO담당자(부)': 'ito_s_mngr'
        }
        db.session.query(ItWas).delete()
        
        for _, row in df.iterrows():
            config_id = str(row.get('구성번호')).strip()
            if not config_id or config_id == 'nan':
                continue
                
            item = ItWas(config_id=config_id)
            db.session.add(item)
            
            for kor, eng in mapping.items():
                if kor in row:
                    val = str(row[kor]) if pd.notna(row[kor]) else None
                    setattr(item, eng, val)
            
            item.user_id = g.user.username

    def import_web(self, df):
        mapping = {
            '구성번호': 'config_id',
            '구성명': 'config_name',
            '설치호스트명': 'host_id',
            '업무시스템': 'biz_system',
            '업무팀': 'biz_team',
            'OS대표IP (GW기준)': 'gw_ip',
            '서비스IP': 'service_ip',
            '운용환경': 'run_env',
            '구성상태': 'config_status',
            '설치계정명': 'install_user',
            'Webtob버전': 'webtob_version',
            'OS종류': 'os_type',
            'OS버전': 'os_ver',
            '노드포트': 'node_port',
            'SSL사용여부': 'ssl_yn',
            'EV인증서여부': 'ev_cert_yn',
            'WEB서버위치': 'server_loc',
            'OS커널': 'os_kernel',
            'CPU (Core)': 'cpu_core',
            'MEM (GB)': 'mem_gb',
            '하드웨어네임': 'hw_name',
            '하드웨어그룹': 'hw_group',
            '담당팀': 'dept_team',
            'KDB담당자(정)': 'kdb_p_mngr',
            'KDB담당자(부)': 'kdb_s_mngr',
            'ITO담당자(정)': 'ito_p_mngr',
            'ITO담당자(부)': 'ito_s_mngr'
        }
        db.session.query(ItWeb).delete()

        for _, row in df.iterrows():
            config_id = str(row.get('구성번호')).strip()
            if not config_id or config_id == 'nan':
                continue

            item = ItWeb(config_id=config_id)
            db.session.add(item)

            for kor, eng in mapping.items():
                if kor in row:
                    val = str(row[kor]) if pd.notna(row[kor]) else None
                    setattr(item, eng, val)
            
            item.user_id = g.user.username

appbuilder.add_view(
    ItWasModelView,
    "IT WAS 구성정보",
    icon="fa-server",
    category="Tools"
)
appbuilder.add_view(
    ItWebModelView,
    "IT WEB 구성정보",
    icon="fa-globe",
    category="Tools"
)
appbuilder.add_separator("Tools")
appbuilder.add_view(
    ItExcelImportView,
    "Excel 파일 업로드",
    icon="fa-upload",
    category="Tools"
)
