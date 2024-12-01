"""empty message

Revision ID: a744f38b64ef
Revises: 2d7cc3818593
Create Date: 2021-07-20 09:57:03.407173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a744f38b64ef'
down_revision = '2d7cc3818593'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_ag_result_host_id'), 'ag_result', ['host_id'], unique=False)
    op.create_index(op.f('ix_ag_result_key_value1'), 'ag_result', ['key_value1'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_ag_result_key_value1'), table_name='ag_result')
    op.drop_index(op.f('ix_ag_result_host_id'), table_name='ag_result')
    # ### end Alembic commands ###
