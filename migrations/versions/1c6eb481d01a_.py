"""empty message

Revision ID: 1c6eb481d01a
Revises: a3e692668a62
Create Date: 2022-03-26 16:09:51.486112

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1c6eb481d01a'
down_revision = 'a3e692668a62'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mw_was', sa.Column('license_cpu', sa.Integer(), nullable=True, comment='License CPU'))
    op.add_column('mw_was', sa.Column('license_edition', sa.String(length=50), nullable=True, comment='License edition'))
    op.add_column('mw_was', sa.Column('license_hostname', sa.String(length=50), nullable=True, comment='License hostname'))
    op.add_column('mw_was', sa.Column('license_type', sa.String(length=50), nullable=True, comment='License type'))
    op.add_column('mw_was', sa.Column('license_issue_date', sa.DateTime(), nullable=True, comment='License 발급일'))
    op.add_column('mw_was', sa.Column('license_due_date', sa.DateTime(), nullable=True, comment='License 만료일'))
    op.add_column('mw_was', sa.Column('license_object', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='License 정보'))
    op.add_column('mw_web', sa.Column('license_cpu', sa.Integer(), nullable=True, comment='License CPU'))
    op.add_column('mw_web', sa.Column('license_edition', sa.String(length=50), nullable=True, comment='License edition'))
    op.add_column('mw_web', sa.Column('license_hostname', sa.String(length=50), nullable=True, comment='License hostname'))
    op.add_column('mw_web', sa.Column('license_type', sa.String(length=50), nullable=True, comment='License type'))
    op.add_column('mw_web', sa.Column('license_issue_date', sa.DateTime(), nullable=True, comment='License 발급일'))
    op.add_column('mw_web', sa.Column('license_due_date', sa.DateTime(), nullable=True, comment='License 만료일'))
    op.add_column('mw_web', sa.Column('license_object', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='License 정보'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('mw_web', 'license_object')
    op.drop_column('mw_web', 'license_due_date')
    op.drop_column('mw_web', 'license_issue_date')
    op.drop_column('mw_web', 'license_type')
    op.drop_column('mw_web', 'license_hostname')
    op.drop_column('mw_web', 'license_edition')
    op.drop_column('mw_web', 'license_cpu')
    op.drop_column('mw_was', 'license_object')
    op.drop_column('mw_was', 'license_due_date')
    op.drop_column('mw_was', 'license_issue_date')
    op.drop_column('mw_was', 'license_type')
    op.drop_column('mw_was', 'license_hostname')
    op.drop_column('mw_was', 'license_edition')
    op.drop_column('mw_was', 'license_cpu')
    # ### end Alembic commands ###