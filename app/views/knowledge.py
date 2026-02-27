from flask import g, redirect, render_template, Response, send_file, request, jsonify
from flask_babel import lazy_gettext
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, expose, has_access
from flask_appbuilder.actions import action
from flask_appbuilder.api import BaseApi, expose, protect
from flask_appbuilder.filemanager import get_file_original_name, FileManager, uuid_namegen
from wtforms import TextAreaField, DateTimeField
from flask_appbuilder.fieldwidgets import DateTimePickerWidget
from app import app, db, appbuilder, con_val, PLANTUML_URL
from app.models.knowledge import UtTag, UtTagKm, UtFile, UtResource, UtResourceAddedText, UtHtmlContent\
    , UtMdContent
from app.models.common import get_user, get_date, get_uuid
from .common import FilterStartsWithFunction, FilterContainsFunction, TagType, TagMustContains\
    , ListAdvanced, ShowWithIds, get_group_str
from app.sqls.monitor import select_row
from app.mail_sender import send_mail
from app.file_manager.s3.filemanager import S3FileManager, S3FileUploadField
from datetime import datetime
import re
import zlib
import base64
import requests

@db.event.listens_for(UtFile, 'before_insert')
def set_file_name(mapper, connection, target):
    target.file_name = get_file_original_name(str(target.file))    

@db.event.listens_for(UtMdContent, 'before_update')
def update_md_content_update(mapper, connection, target):
    target.update_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@db.event.listens_for(UtHtmlContent, 'before_update')
def update_html_content_update(mapper, connection, target):
    target.update_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class UtTagModelView(ModelView):

    datamodel = SQLAInterface(UtTag)
    
    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "Tag"
    list_columns = ['tag', 'label', 'ut_child_tag', 'ut_parent_tag']
    label_columns = {'ut_child_tag':'하위Tag'
                    ,'ut_parent_tag':'상위Tag'
                    }

    edit_exclude_columns = ['user_id', 'create_on']
    add_exclude_columns = ['user_id', 'create_on']

    extra_args = {
        'inputList':[
         {'text':'TAG 검색','id':'tag-name','combind':'0','condition':'_flt_2_tag=','size':20}
        ]
        }

class UtTagKmModelView(ModelView):

    datamodel = SQLAInterface(UtTagKm)
    
    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "지식관리 Tag"
    list_columns = ['tag', 'label', 'value1', 'ut_child_tag', 'ut_parent_tag']
    label_columns = {'ut_child_tag':'하위Tag'
                    ,'ut_parent_tag':'상위Tag'
                    }

    edit_exclude_columns = ['user_id', 'create_on']
    add_exclude_columns = ['user_id', 'create_on']

    extra_args = {
        'inputList':[
         {'text':'TAG 검색','id':'tag-name','combind':'0','condition':'_flt_2_tag=','size':20}
        ]
        }

class UtResourceAddedTextModelView(ModelView):

    datamodel = SQLAInterface(UtResourceAddedText)
    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced


    list_title   = "Resource 부가정보"
    list_columns = ['ut_tag','ut_resource','resource_added_name']
    edit_exclude_columns = ['user_id','create_on']
    add_exclude_columns = ['user_id','create_on']

    validators_columns = {
                    'ut_tag':[TagType('부가정보')]
                }

class UtHtmlContentModelView(ModelView):

    datamodel = SQLAInterface(UtHtmlContent)
    add_template = 'add_summer.html'
    edit_template = 'edit_summer.html'

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced


    list_title   = "지식정보(html 형식)"
    list_columns = ['show_html','ut_tag','content_name','update_on','create_on','pop_html']
    label_columns = {'show_html':'조회','update_on':'최종수정일시','create_on':'최초생성일시'}

    edit_exclude_columns = ['user_id','group_id', 'create_on','update_on']
    add_exclude_columns = ['user_id','group_id', 'create_on','update_on']

    base_permissions = ['can_list', 'can_add', 'can_edit', 'can_delete']
    #add_form_extra_fields = {'ut_file':TextAreaField('file upload',widget=BS3TextAreaFieldWidget())}
    base_order = ('create_on', 'desc')

    base_filters = [['group_id', FilterStartsWithFunction, get_group_str]]

    extra_args = {
        'summer_column':'content_html',
        'tags_column':'search_tags',
        'plantuml_url':PLANTUML_URL+"/png/",
        'selectList':[
         {'text':'지식유형','id':'tag-selector','combind':'1','type':'parent','condition':{'operator':'and','column':'tag','value':'지식유형'}}
        ],
        'inputList':[
         {'text':'제목 검색','id':'content-name','combind':'1','condition':'_flt_2_content_name=','size':12}
        ,{'text':'TAG 검색','id':'search-tags','combind':'1','condition':'_flt_2_search_tags=','size':12}
        ]
    }

    @action("copyHtmlContents"
            ,"지식 Copy 하기"
            ,"Copy the selected Contents?"
            ,icon="fa-copy"
            ,single=False
    )
    def copyHtmlContents(self, items):
        self.update_redirect()
        for item in items:
            new_content              = item.__class__()
            new_content.content_id   = get_uuid()
            new_content.content_html = item.content_html
            new_content.content_name = "Copied_" + item.content_name
            new_content.search_tags = item.search_tags
            new_content.update_on    = get_date()
            new_content.create_on    = get_date()
            new_content.ut_file      = item.ut_file
            new_content.ut_tag       = item.ut_tag
            
            self.datamodel.add(new_content)
        return redirect(self.get_redirect())

    @action("sendEmail","Send Email","","fa-rocket",single=False)
    def sendEmail(self, items):

        for item in items:

            ut_tag = item.ut_tag
            emails = []
            for tag in ut_tag:
                if con_val['TAG_EMAILS'] in tag.tag:
                    if tag.value1:
                        emails = emails + tag.value1.split(',')

            emails = list(set(filter(None, emails)))

            ut_file = item.ut_file

            files = []
            for f in ut_file:
                s3_fm = S3FileManager()
                try:
                    file_content = s3_fm.get_file(f.file)
                    files.append((f.file_name, file_content))
                except Exception as e:
                    log.error(f"Failed to get file from S3: {f.file}, {e}")

            if not emails:
                continue

            send_mail(con_val['KDB_SMTP_IP'], con_val['KDB_SMTP_PORT']
                    , con_val.get('SMTP_SENDER', ''), g.user.username
                    , emails, item.content_name, item.content_html
                    , files=files
                    , use_tls=con_val.get('SMTP_USE_TLS', False)
                    , username=con_val.get('SMTP_USERNAME')
                    , password=con_val.get('SMTP_PASSWORD'))

        self.update_redirect()
        return redirect(self.get_redirect())

    def _link_uploaded_files(self, item):
        """Link drag-and-drop uploaded files to the HtmlContent item."""
        uploaded_file_ids = request.form.get('uploaded_file_ids', '')
        if uploaded_file_ids:
            file_ids = [int(fid.strip()) for fid in uploaded_file_ids.split(',') if fid.strip()]
            if file_ids:
                existing_ids = [f.id for f in item.ut_file]
                for fid in file_ids:
                    if fid not in existing_ids:
                        file_obj = db.session.query(UtFile).get(fid)
                        if file_obj:
                            item.ut_file.append(file_obj)
                db.session.commit()

    def post_add(self, item):
        self._link_uploaded_files(item)

    def post_update(self, item):
        self._link_uploaded_files(item)

class UtMdContentModelView(ModelView):

    datamodel = SQLAInterface(UtMdContent)
    add_template = 'add_md2.html'
    edit_template = 'edit_md2.html'

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "지식정보(Markdown 형식)"
    list_columns = ['show_md','ut_tag','content_name','update_on', 'user_id', 'create_on','download']
    label_columns = {'show_md':'조회','update_on':'최종수정일시', 'user_id':'작성자 ID', 'create_on':'최초생성일시'}

    edit_exclude_columns = ['user_id', 'create_on']
    add_exclude_columns = ['user_id', 'create_on','update_on']

    base_permissions = ['can_list', 'can_add', 'can_edit', 'can_delete']
    #add_form_extra_fields = {'ut_file':TextAreaField('file upload',widget=BS3TextAreaFieldWidget())}
    base_order = ('create_on', 'desc')

    base_filters = [['group_id', FilterContainsFunction, get_group_str]]

    edit_form_extra_fields = {
        'update_on': DateTimeField('수정 일시', widget=DateTimePickerWidget())
    }

    extra_args = {
        'summer_column':'content_md',
        'tags_column':'search_tags',
        'selectList':[
         {'text':'지식유형','id':'tag-selector','combind':'1','type':'parent','condition':{'operator':'and','column':'tag','value':'지식유형'}}
        ],
        'inputList':[
         {'text':'제목 검색','id':'content-name','combind':'1','condition':'_flt_2_content_name=','size':12}
        ,{'text':'TAG 검색','id':'search-tags','combind':'1','condition':'_flt_2_search_tags=','size':12}
        ]
    }

    @action("copyMdContents"
            ,"지식 Copy 하기"
            ,"Copy the selected Contents?"
            ,icon="fa-copy"
            ,single=False
    )
    def copyMdContents(self, items):
        self.update_redirect()
        for item in items:
            new_content              = item.__class__()
            new_content.content_id   = get_uuid()
            new_content.content_md = item.content_md
            new_content.content_name = "Copied_" + item.content_name
            new_content.search_tags = item.search_tags
            new_content.update_on    = get_date()
            new_content.create_on    = get_date()
            new_content.ut_file      = item.ut_file
            new_content.ut_tag       = item.ut_tag
            
            self.datamodel.add(new_content)
        return redirect(self.get_redirect())

    @action("sendMdEmail"
            ,"Send Email"
            ,""
            ,icon="fa-rocket"
            ,single=False
    )
    def sendMdEmail(self, items):
        import markdown

        for item in items:

            ut_tag = item.ut_tag
            emails = []
            for tag in ut_tag:
                if con_val['TAG_EMAILS'] in tag.tag:
                    if tag.value1:
                        emails = emails + tag.value1.split(',')

            emails = list(set(filter(None, emails)))

            ut_file = item.ut_file

            files = []
            for f in ut_file:
                s3_fm = S3FileManager()
                try:
                    file_content = s3_fm.get_file(f.file)
                    files.append((f.file_name, file_content))
                except Exception as e:
                    log.error(f"Failed to get file from S3: {f.file}, {e}")

            if not emails:
                continue

            # Convert Markdown to HTML
            md_content = item.content_md or ''

            # Replace Mermaid blocks with CID image tags and fetch image data
            inline_images = []
            mermaid_counter = 0

            def mermaid_replacer(match):
                nonlocal mermaid_counter
                code = match.group(1).strip()
                try:
                    zlib_compressed = zlib.compress(code.encode('utf-8'), level=9)
                    encoded = base64.urlsafe_b64encode(zlib_compressed).decode('utf-8')
                    kroki_url = con_val.get('KROKI_URL', 'http://mwm-kroki:8000').rstrip('/')
                    
                    # Fetch image data from local Kroki
                    img_resp = requests.get(f"{kroki_url}/mermaid/png/{encoded}", timeout=10)
                    if img_resp.status_code == 200:
                        mermaid_counter += 1
                        cid = f"mermaid_{mermaid_counter}"
                        inline_images.append((cid, img_resp.content))
                        return f'<img src="cid:{cid}" style="max-width:100%; border:1px solid #eee; margin:10px 0;">'
                    else:
                        log.error(f"Kroki fetch failed: {img_resp.status_code}")
                        return f"<pre>{code}</pre>"
                except Exception as e:
                    log.error(f"Mermaid conversion failed: {e}")
                    return match.group(0)

            md_content = re.sub(r'```mermaid\s+(.*?)\s+```', mermaid_replacer, md_content, flags=re.DOTALL)

            html_content = markdown.markdown(
                md_content,
                extensions=['fenced_code', 'tables', 'codehilite', 'toc', 'nl2br']
            )

            # Wrap with basic styling for email readability
            styled_html = '''<div style="font-family: 'Malgun Gothic','맑은 고딕',sans-serif; font-size: 14px; line-height: 1.6; color: #333;">
<style>
table { border-collapse: collapse; margin: 10px 0; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background-color: #f2f2f2; }
pre { background: #f6f8fa; padding: 12px; border-radius: 6px; border: 1px solid #d0d7de; overflow-x: auto; }
code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 13px; }
pre code { background: none; padding: 0; }
blockquote { border-left: 4px solid #dfe2e5; padding: 0 15px; color: #6a737d; margin: 10px 0; }
h1, h2, h3 { border-bottom: 1px solid #eaecef; padding-bottom: 5px; }
</style>
''' + html_content + '</div>'

            send_mail(con_val['KDB_SMTP_IP'], con_val['KDB_SMTP_PORT']
                    , con_val.get('SMTP_SENDER', ''), g.user.username
                    , emails, item.content_name, styled_html
                    , files=files
                    , use_tls=con_val.get('SMTP_USE_TLS', False)
                    , username=con_val.get('SMTP_USERNAME')
                    , password=con_val.get('SMTP_PASSWORD')
                    , inline_images=inline_images)

        self.update_redirect()
        return redirect(self.get_redirect())

    def _link_uploaded_files(self, item):
        """Link drag-and-drop uploaded files to the MdContent item."""
        uploaded_file_ids = request.form.get('uploaded_file_ids', '')
        if uploaded_file_ids:
            file_ids = [int(fid.strip()) for fid in uploaded_file_ids.split(',') if fid.strip()]
            if file_ids:
                existing_ids = [f.id for f in item.ut_file]
                for fid in file_ids:
                    if fid not in existing_ids:
                        file_obj = db.session.query(UtFile).get(fid)
                        if file_obj:
                            item.ut_file.append(file_obj)
                db.session.commit()

    def post_add(self, item):
        self._link_uploaded_files(item)

    def post_update(self, item):
        self._link_uploaded_files(item)

class UtFileModelView(ModelView):
    datamodel = SQLAInterface(UtFile)

    label_columns = {'ut_html_content':"지식정보(Html)", 'ut_md_content':"지식정보(Markdown)", "file_name": "File Name", "download": "Download"}
    add_columns   = ['ut_html_content','ut_md_content','file']
    edit_columns  = ['ut_html_content','ut_md_content','file']
    list_columns  = ['ut_html_content','ut_md_content','file_name','file','download','create_on']
    show_columns  = ['file', 'file_name','download', 'user_id','create_on']

    base_order = ('create_on', 'desc')

    edit_form_extra_fields = add_form_extra_fields = {
        "file": S3FileUploadField("S3 File",
                                    description="",
                                    filemanager=S3FileManager,
                                )
    }

    def pre_delete(self, rel_obj):
        filename = getattr(rel_obj, 'file')
        file_obj = S3FileManager()
        file_obj.delete_file(filename)

class UtResourceModelView(ModelView):

    datamodel = SQLAInterface(UtResource)
    
    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "Resource"
    list_columns = ['resource_id', 'resource_name', 'host_id', 'mw_server.ip_address', 'service_port', 'sys_user', 't__landscape', 't__resourcetype', 't__incharge', 't__ha', 'resource_description']
    edit_exclude_columns = ['user_id','create_on']
    add_exclude_columns = ['user_id','create_on']


    description_columns = {'ut_tag':"'리소스유형', 'LANDSCAPE', '시스템'은 필수입니다."}
    validators_columns = {
                    'ut_tag':[TagMustContains(['리소스유형','LANDSCAPE'])]
                }

    extra_args = {
        'selectList':[
         {'text':'리소스유형','id':'tag-selector','combind':'0','type':'parent','condition':{'operator':'and','column':'tag','value':'리소스유형'}}
         ,{'text':'LANDSCAPE','id':'tag-selector','combind':'0','type':'parent','condition':{'operator':'and','column':'tag','value':'LANDSCAPE'}}
        ]
        }

    related_views = [UtResourceAddedTextModelView]

class UtApi(BaseApi):

    route_base = '/ut'

    @expose('/htmlcontent/<param>', methods=['GET'])
    @has_access
    def uthtmlcontent(self, param=None):

        title = ''
        html = ''
        update_on = ''
        files = []

        row, _ = select_row('ut_html_content',{'id':int(param)})

        if row:
            title = row.content_name
            html  = row.content_html
            update_on = row.update_on.strftime("%Y-%m-%d %H:%M:%S")
            
            if row.ut_file:
                for f in row.ut_file:
                    files.append(dict(
                        file_name=f.file_name
                       ,file=f.file
                    ))

        return render_template('show_raw.html'\
            , title=title
            , html=html
            , update_on=update_on
            , update_page='/uthtmlcontentmodelview/edit/'+param
            , files=files
            , base_template=appbuilder.base_template
            , appbuilder=appbuilder
            )

    @expose('/mdcontent/<param>', methods=['GET'])
    @has_access
    def utmdcontent(self, param=None):

        title = ''
        html = ''
        update_on = ''
        files = []

        row, _ = select_row('ut_md_content',{'id':int(param)})

        if row:
            title = row.content_name
            md  = row.content_md
            update_on = row.update_on.strftime("%Y-%m-%d %H:%M:%S")
            
            if row.ut_file:
                for f in row.ut_file:
                    files.append(dict(
                        file_name=f.file_name
                       ,file=f.file
                    ))

        return render_template('show_md2.html'\
            , plantuml_url=PLANTUML_URL+"/png/"
            , title=title
            , md=md
            , update_on=update_on
            , update_page='/utmdcontentmodelview/edit/'+param
            , files=files
            , base_template=appbuilder.base_template
            , appbuilder=appbuilder
            )

    @expose('/mdcontent.download/<content_id>', methods=['GET'])
    @has_access
    def mddownload(self, content_id):

        row, _ = select_row('ut_md_content',{'content_id':content_id})

        md = row.content_md if row else ''

        return Response(md, 
            mimetype="text/plain",
            headers={"Content-Disposition":"attachment;filename="+content_id+".md"})

    @expose('/upload_file', methods=['POST'])
    @has_access
    def upload_file(self):
        """Drag & Drop file upload API.
        Saves file to S3 and creates UtFile record.
        Returns file_id, file_name, download_url.
        """
        if 'file' not in request.files:
            return jsonify(error='No file provided'), 400

        file = request.files['file']
        if not file.filename:
            return jsonify(error='Empty filename'), 400

        try:
            # Generate unique filename and save to S3
            file_manager = S3FileManager()
            s3_filename = uuid_namegen(file)
            file_data = file.read()
            file_manager.save_file(file_data, s3_filename)

            # Create UtFile record
            ut_file = UtFile()
            ut_file.file = s3_filename
            ut_file.file_name = file.filename
            ut_file.user_id = g.user.username if g.user else 'system'
            db.session.add(ut_file)
            db.session.commit()

            return jsonify(
                file_id=ut_file.id,
                file_name=file.filename,
                s3_filename=s3_filename,
                download_url='/common/download/' + s3_filename
            ), 200

        except Exception as e:
            db.session.rollback()
            return jsonify(error=str(e)), 500

#appbuilder.add_separator("Server")
appbuilder.add_separator("Server")
appbuilder.add_view(
    UtResourceModelView,
    "Resource",
    icon="fa-folder-open-o",
    category="Server",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    UtResourceAddedTextModelView,
    "Resource 부가정보(TEXT)",
    icon="fa-folder-open-o",
    category="Server",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    UtTagModelView,
    "마스터정보Tag",
    icon="fa-folder-open-o",
    category="지식관리",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    UtTagKmModelView,
    "지식관리Tag",
    icon="fa-folder-open-o",
    category="지식관리",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    UtHtmlContentModelView,
    "지식정보(Html)",
    icon="fa-folder-open-o",
    category="지식관리",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    UtMdContentModelView,
    "지식정보(Markdown)",
    icon="fa-folder-open-o",
    category="지식관리",
    category_icon="fa-envelope"
)
appbuilder.add_view(
    UtFileModelView,
    "지식정보(File)",
    icon="fa-folder-open-o",
    category="지식관리",
    category_icon="fa-envelope"
)
appbuilder.add_api(UtApi)
