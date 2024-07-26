
from . import db
from sqlalchemy.sql import func
from .sqls_monitor import insertRow, selectRow
from sys import exc_info

def insertTag(tag):

    rtn = 0
    row, _ = selectRow('ut_tag',{'tag':tag})
    if not row:
        insert_dict = dict(tag = tag)
        tag_id, _ = insertRow('ut_tag', insert_dict)
        rtn = tag_id
    else:
        rtn = row.id
    
    return rtn