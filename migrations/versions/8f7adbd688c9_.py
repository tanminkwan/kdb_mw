"""empty message

Revision ID: 8f7adbd688c9
Revises: fdb8d0501ae6
Create Date: 2023-03-14 12:38:13.841532

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f7adbd688c9'
down_revision = 'fdb8d0501ae6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mw_application', sa.Column('filtered_text', sa.Text(), nullable=True, comment='색출 정보'))
    op.add_column('mw_application', sa.Column('filtered_update_date', sa.DateTime(), nullable=True, comment='색출 정보 갱신일시'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('mw_application', 'filtered_update_date')
    op.drop_column('mw_application', 'filtered_text')
    # ### end Alembic commands ###