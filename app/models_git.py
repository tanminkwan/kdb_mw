from flask import g, Markup, url_for
from flask_appbuilder import Model
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, String, ForeignKey\
, DateTime, Enum, UniqueConstraint, ForeignKeyConstraint\
, Table, Date
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from flask_appbuilder.models.mixins import FileColumn
from flask_appbuilder.models.decorators import renders
from flask_appbuilder.filemanager import get_file_original_name
from .models_com import get_user, WasInstanceStatusEnum, LocationEnum

class GtGroupUsers(Model):
    __tablename__ = "gt_group_users"
    t__table_comment = {"comment":"GitLab group id 별 user 매핑"}
    function_comments = {}

    id               = Column(Integer, primary_key=True, nullable=False)
    group_id         = Column(String(30), nullable=False)
    user_ids         = Column(String(500), nullable=False)
    user_id          = Column(String(50), default=get_user, nullable=False)
    create_on        = Column(DateTime(), default=datetime.now, nullable=False)    
    UniqueConstraint(group_id)

    __table_args__ = (
        t__table_comment,
    )
    
    def __repr__(self):
        return self.group_id