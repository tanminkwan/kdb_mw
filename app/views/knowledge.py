from flask import g, redirect, render_template, Response
from flask_babel import lazy_gettext
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, expose, has_access
from flask_appbuilder.actions import action
from flask_appbuilder.api import BaseApi, expose, protect
from flask_appbuilder.filemanager import get_file_original_name, FileManager
from wtforms import TextAreaField
from flask_appbuilder.fieldwidgets import BS3TextAreaFieldWidget
from app import db, appbuilder, con_val
from app.models.knowledge import UtTag, UtTagKm, UtFile, UtResource, UtResourceAddedText, UtHtmlContent\
    , UtMdContent
from app.models.common import get_user, get_date, get_uuid
from .common import FilterStartsWithFunction, FilterContainsFunction, TagType, TagMustContains\
    , ListAdvanced, ShowWithIds, get_group_str
from app.sqls.monitor import select_row
from app.auto_report.testSmtp import send_kdbMail


@db.event.listens_for(UtFile, 'before_insert')
def set_file_name(mapper, connection, target):
    target.file_name = get_file_original_name(str(target.file))    

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

    edit_exclude_columns = ['user_id','group_id', 'create_on']
    add_exclude_columns = ['user_id','group_id', 'create_on','update_on']

    base_permissions = ['can_list', 'can_add', 'can_edit', 'can_delete']
    #add_form_extra_fields = {'ut_file':TextAreaField('file upload',widget=BS3TextAreaFieldWidget())}
    base_order = ('create_on', 'desc')

    base_filters = [['group_id', FilterStartsWithFunction, get_group_str]]

    extra_args = {
        'summer_column':'content_html',
        'tags_column':'search_tags',
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
                if con_val['TAG_ONCHARGE'] in tag.tag\
                    or con_val['TAG_EMAILS'] in tag.tag:
                    emails = emails + tag.value1.split(',')

            emails = list(set(filter(None, emails)))

            ut_file = item.ut_file

            files = []
            file_names = []
            for f in ut_file:
                fm = FileManager()
                fullname = fm.get_path(f.file)
                files.append(fullname)
                file_names.append(f.file_name)

            if not emails:
                continue

            send_kdbMail(con_val['KDB_SMTP_IP'],con_val['KDB_SMTP_PORT']\
                    , 'leebalso@kdb.co.kr', g.user.username\
                    , emails, item.content_name, item.content_html\
                    , files, file_names=file_names)

            #db.session.commit()

        self.update_redirect()
        return redirect(self.get_redirect())

class UtMdContentModelView(ModelView):

    datamodel = SQLAInterface(UtMdContent)
    add_template = 'add_md2.html'
    edit_template = 'edit_md2.html'

    list_template = 'listWithJson.html'
    list_widget   = ListAdvanced

    list_title   = "지식정보(Markdown 형식)"
    list_columns = ['show_md','ut_tag','content_name','update_on','create_on','download']
    label_columns = {'show_md':'조회','update_on':'최종수정일시','create_on':'최초생성일시'}

    edit_exclude_columns = ['user_id', 'create_on']
    add_exclude_columns = ['user_id', 'create_on','update_on']

    base_permissions = ['can_list', 'can_add', 'can_edit', 'can_delete']
    #add_form_extra_fields = {'ut_file':TextAreaField('file upload',widget=BS3TextAreaFieldWidget())}
    base_order = ('create_on', 'desc')

    base_filters = [['group_id', FilterContainsFunction, get_group_str]]

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

class UtFileModelView(ModelView):
    datamodel = SQLAInterface(UtFile)

    label_columns = {'ut_html_content':"지식정보","file_name": "File Name", "download": "Download"}
    add_columns   = ['ut_html_content','file']
    edit_columns  = ['ut_html_content','file']
    list_columns  = ['ut_html_content','file_name','download','create_on']
    show_columns  = ['file', 'file_name','download', 'user_id','create_on']

    base_order = ('create_on', 'desc')

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
