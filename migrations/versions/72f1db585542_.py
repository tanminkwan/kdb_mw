"""empty message

Revision ID: 72f1db585542
Revises: c2b7aca1c0bd
Create Date: 2021-08-18 15:18:32.300544

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72f1db585542'
down_revision = 'c2b7aca1c0bd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mo_grid_config', sa.Column('page_dblclick', sa.String(length=100), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('mo_grid_config', 'page_dblclick')
    # ### end Alembic commands ###
