from flask import g
from flask_appbuilder.models.sqla.filters import BaseFilter, get_field_setup_query
from flask_appbuilder.fieldwidgets import BS3TextFieldWidget
from flask_appbuilder.widgets import ShowWidget, ListWidget
from wtforms.validators import ValidationError, StopValidation
import enum
from app.sqls.monitor import getLastReportedTime, select_row
from app.models.common import get_group

def get_mw_user():
    roles = [ r.name for r in g.user.roles]
    if 'mw_role' in roles or 'Admin' in roles:
        return ''
    else:
        return g.user.username

def get_group_str():
    roles = [ r.name for r in g.user.roles]
    group = get_group()
    print("Group : ", group)
    if 'Admin' in roles:
        return ''
    elif group:
        return group
    else:
        return 'XXX'

def get_userid():
    return g.user.username

def get_reporttime():
    return getLastReportedTime()

class ShowWithIds(ShowWidget):
    template = 'widgets/showWithIds.html'

class ListAdvanced(ListWidget):
    template = 'widgets/listWithSafeFormatter.html'

class ReadOnlyField(BS3TextFieldWidget):
    def __call__(self, field, **kwargs):
        kwargs['readonly'] = 'true'
        return super(ReadOnlyField, self).__call__(field, **kwargs)

class FilterStartsWithFunction(BaseFilter):
    name = "Filter view with a function"
    arg_name = "eqf"

    def apply(self, query, func):
        query, field = get_field_setup_query(query, self.model, self.column_name)
        return query.filter(field.ilike(func() + "%%"))
    
class FilterContainsFunction(BaseFilter):
    name = "Filter view with a function"
    arg_name = "eqf"

    def apply(self, query, func):
        query, field = get_field_setup_query(query, self.model, self.column_name)
        return query.filter(field.contains(func()))

class RequiredOnContidion(object):

    def __init__(self, fieldname, value, message=None):
        self.fieldname = fieldname
        self.message = message
        self.value = value if isinstance(value, list) else [value] 
        
    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)

        if isinstance(other.data, enum.Enum):
            real_data = other.data.name
        else:
            real_data = other.data
        
        if real_data in self.value and not field.data:
        
            message = self.message
            if message is None:
                message = field.gettext('This field is required')

            #raise ValidationError(message % d)
            raise StopValidation(message)

class ValidateBatchFunctionName:

    def __call__(self, form, field):

        try:
            other = form['command_class']
        except KeyError:
            raise ValidationError(field.gettext(f"Invalid field name 'command_class'."))

        if isinstance(other.data, enum.Enum):
            real_data = other.data.name
        else:
            real_data = other.data

        from app.sqls.batch import batch_function_registry
        
        if real_data == 'ServerFunc' and \
            not batch_function_registry.get(field.data):
            raise StopValidation(field.gettext(f"Invalid Function name : {field.data}."))

class TagType(object):

    def __init__(self, tagtype):
        self.tagtype = tagtype

    def __call__(self, form, field):

        tag = field.data.tag
        
        if not tag.startswith(self.tagtype):
            d = {
                'other_label': self.tagtype,
                'other_name': self.tagtype
            }
            message = field.gettext('\'%(other_name)s\'로 시작하는 Tag를 선택하세요.')

            raise ValidationError(message % d)

class TagMustContains(object):

    def __init__(self, tagtypes):
        self.tagtypes = tagtypes

    def __call__(self, form, field):

        if not field.data:
            raise ValidationError(field.gettext("Tag를 선택하여 주세요."))

        for rec in field.data:
            for tagtype in self.tagtypes:
                if rec.tag.startswith(tagtype):
                    self.tagtypes.remove(tagtype)

        if self.tagtypes:
            t = ','.join(self.tagtypes)
            message = field.gettext("다음 tag type들을 추가하시기 바랍니다. '%s'.") % t
            raise ValidationError(message)