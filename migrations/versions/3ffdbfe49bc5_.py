"""empty message

Revision ID: 3ffdbfe49bc5
Revises: 7412a658f0a8
Create Date: 2022-07-19 09:41:27.863351

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ffdbfe49bc5'
down_revision = '7412a658f0a8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mo_grid_config', sa.Column('default_condition', sa.String(length=1000), nullable=True))
    op.add_column('ut_resource', sa.Column('resource_name', sa.String(length=500), nullable=True, comment='Resource Name'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ut_resource', 'resource_name')
    op.drop_column('mo_grid_config', 'default_condition')
    # ### end Alembic commands ###