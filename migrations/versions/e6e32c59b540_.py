"""empty message

Revision ID: e6e32c59b540
Revises: aceecf2eda13
Create Date: 2022-05-10 14:07:47.328289

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6e32c59b540'
down_revision = 'aceecf2eda13'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mw_was', sa.Column('jeus_properties_text', sa.Text(), nullable=True, comment='jeus properties 정보'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('mw_was', 'jeus_properties_text')
    # ### end Alembic commands ###