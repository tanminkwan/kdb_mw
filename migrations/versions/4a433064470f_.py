"""empty message

Revision ID: 4a433064470f
Revises: 
Create Date: 2021-05-25 13:40:41.859477

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import flask_appbuilder

# revision identifiers, used by Alembic.
revision = '4a433064470f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ag_agent',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent_id', sa.String(length=30), nullable=False),
    sa.Column('agent_name', sa.String(length=300), nullable=True),
    sa.Column('agent_type', sa.Enum('JAVAAGENT', 'WHEREAMI', 'SHIFTSIS', name='agenttypeenum'), nullable=False),
    sa.Column('host_id', sa.String(length=30), nullable=True),
    sa.Column('ip_address', sa.String(length=20), nullable=False),
    sa.Column('approved_yn', postgresql.ENUM('YES', 'NO', name='ynenum', create_type=False), server_default='NO', nullable=False),
    sa.Column('last_checked_date', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agent_id')
    )
    op.create_table('ag_agent_group',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent_group_id', sa.String(length=30), nullable=False),
    sa.Column('agent_group_name', sa.String(length=300), nullable=True),
    sa.Column('agent_type', sa.Enum('JAVAAGENT', 'WHEREAMI', 'SHIFTSIS', name='agenttypeenum'), nullable=True),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agent_group_id')
    )
    op.create_table('ag_command_type',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('command_type_id', sa.String(length=30), nullable=False),
    sa.Column('command_type_name', sa.String(length=100), nullable=True),
    sa.Column('command_class', sa.Enum('ReadPlainFile', 'ExeScript', 'ExeShell', 'ExeAgentFunc', 'DownloadFile', 'UploadFile', name='commandclassenum'), nullable=True),
    sa.Column('target_file_path', sa.String(length=300), nullable=True),
    sa.Column('target_file_name', sa.String(length=100), nullable=True),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('command_type_id')
    )
    op.create_table('ag_file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent_type', sa.Enum('JAVAAGENT', 'WHEREAMI', 'SHIFTSIS', name='agenttypeenum'), nullable=False),
    sa.Column('file_name', sa.String(length=50), nullable=False),
    sa.Column('file_version', sa.String(length=50), nullable=False),
    sa.Column('file', flask_appbuilder.models.mixins.FileColumn(), nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agent_type', 'file_name', 'file_version')
    )
    op.create_table('ag_agent_agentgroup',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_of_agent_group', sa.Integer(), nullable=True),
    sa.Column('id_of_agent', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_of_agent'], ['ag_agent.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_of_agent_group'], ['ag_agent_group.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ag_command_master',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('command_id', sa.String(length=30), nullable=False),
    sa.Column('command_type_id', sa.String(length=30), nullable=False),
    sa.Column('periodic_type', sa.Enum('IMMEDIATE', 'ONETIME', 'PERIODIC', name='periodictypeenum'), nullable=True),
    sa.Column('time_to_exe', sa.DateTime(), nullable=True),
    sa.Column('time_to_stop', sa.DateTime(), nullable=True),
    sa.Column('cycle_to_exe', sa.Integer(), nullable=True),
    sa.Column('interval_type', sa.Enum('minutes', 'hours', 'days', name='intervaltypeenum'), nullable=True),
    sa.Column('additional_params', sa.String(length=1000), nullable=True),
    sa.Column('publish_yn', postgresql.ENUM('YES', 'NO', name='ynenum', create_type=False), server_default='NO', nullable=False),
    sa.Column('cancel_yn', postgresql.ENUM('YES', 'NO', name='ynenum', create_type=False), server_default='NO', nullable=False),
    sa.Column('finished_yn', postgresql.ENUM('YES', 'NO', name='ynenum', create_type=False), server_default='NO', nullable=True),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['command_type_id'], ['ag_command_type.command_type_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('command_id')
    )
    op.create_table('ag_agent_commandmaster',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_of_agent', sa.Integer(), nullable=True),
    sa.Column('id_of_command_master', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_of_agent'], ['ag_agent.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_of_command_master'], ['ag_command_master.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ag_agentgroup_commandmaster',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_of_agent_group', sa.Integer(), nullable=True),
    sa.Column('id_of_command_master', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_of_agent_group'], ['ag_agent_group.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_of_command_master'], ['ag_command_master.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ag_command_detail',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('command_id', sa.String(length=30), nullable=False),
    sa.Column('agent_id', sa.String(length=30), nullable=False),
    sa.Column('repetition_seq', sa.Integer(), nullable=False),
    sa.Column('command_type_id', sa.String(length=30), nullable=False),
    sa.Column('command_class', sa.Enum('ReadPlainFile', 'ExeScript', 'ExeShell', 'ExeAgentFunc', 'DownloadFile', 'UploadFile', name='commandclassenum'), nullable=True),
    sa.Column('target_file_path', sa.String(length=300), nullable=True),
    sa.Column('target_file_name', sa.String(length=100), nullable=True),
    sa.Column('additional_params', sa.String(length=1000), nullable=True),
    sa.Column('command_status', sa.Enum('CREATE', 'SENDED', 'COMPLITED', name='commandstatusenum'), nullable=False),
    sa.Column('result_received_date', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['command_id'], ['ag_command_master.command_id'], ),
    sa.ForeignKeyConstraint(['command_type_id'], ['ag_command_type.command_type_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('command_id', 'agent_id', 'repetition_seq')
    )
    op.create_table('ag_result',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('command_id', sa.String(length=30), nullable=False),
    sa.Column('agent_id', sa.String(length=30), nullable=False),
    sa.Column('repetition_seq', sa.Integer(), nullable=False),
    sa.Column('host_id', sa.String(length=30), nullable=False),
    sa.Column('key_value1', sa.String(length=200), nullable=False),
    sa.Column('key_value2', sa.String(length=200), nullable=False),
    sa.Column('result_text', sa.Text(), nullable=True),
    sa.Column('result_status', sa.Enum('CREATE', 'ERROR', 'NOCHANGE', 'COMPLITED', name='resultstatusenum'), server_default='CREATE', nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('create_on', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['command_id', 'agent_id', 'repetition_seq'], ['ag_command_detail.command_id', 'ag_command_detail.agent_id', 'ag_command_detail.repetition_seq'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('command_id', 'agent_id', 'repetition_seq', 'host_id', 'key_value1', 'key_value2')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ag_result')
    op.drop_table('ag_command_detail')
    op.drop_table('ag_agentgroup_commandmaster')
    op.drop_table('ag_agent_commandmaster')
    op.drop_table('ag_command_master')
    op.drop_table('ag_agent_agentgroup')
    op.drop_table('ag_file')
    op.drop_table('ag_command_type')
    op.drop_table('ag_agent_group')
    op.drop_table('ag_agent')
    # ### end Alembic commands ###