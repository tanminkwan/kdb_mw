"""empty message

Revision ID: f311ae21288c
Revises: 4a433064470f
Create Date: 2021-05-27 10:33:43.884471

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f311ae21288c'
down_revision = '4a433064470f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ag_agent', sa.Column('agent_version', sa.String(length=50), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ag_agent', 'agent_version')
    # ### end Alembic commands ###
