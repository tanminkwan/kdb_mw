import logging
from . import db, scheduler
from datetime import datetime, timedelta
from sqlalchemy.sql import select, update
from app.models.agent import AgCommandType, AgCommandMaster, AgCommandDetail\
    , AgResult, AgAgentGroup, AgAgent
from app.models.common import CommandClassEnum
from app.sqls.agent import finish_commands_by_scheduler, createCommandDetail_bySch\
    , get_commands, get_closeto_token_expiry_bysch, getLastRundatetime
from app.sqls.batch import run_batch_by_scheduler
from app.sqls.monitor import get_not_running_was_list
from app.views.common import call_notification

@scheduler.task('cron', id='job_ag_finish_commands', name='Remove Finished Commands', minute='*/1')
def job_ag_finish_commands():
    finish_commands_by_scheduler()

@scheduler.task('cron', id='job_ag_extend_token_expiry', name='Refrash Token Update to Agents', hour='*/12')
def job_ag_extend_token_expiry():
    get_closeto_token_expiry_bysch(3)

@scheduler.task('cron', id='notify_was_abnormal_status', name='Notify WAS Abnormal Status', minute='*/1')
def notify_was_abnormal_status():
    _, recs, _ = get_not_running_was_list()

    logging.info(f"was_abnormal_status 건수 : {len(recs)}")
    [ call_notification(f" WAS_STATUS: {rec['was_instance_id']}-상태 비정상 ({rec['was_instance_stat']}.{rec['host_id']})") for rec in recs]

#@scheduler.task('cron', id='job_ag_start_jobs', name='Remove Finished Commands', minute='*/1')
@scheduler.task('date', id='job_ag_start_jobs')
def job_ag_start_jobs():
    logging.debug('job_ag_start_jobs is called.')

    commands = get_commands()
    
    for cmd in commands:
        job_ag_create_job(cmd)

def job_ag_create_job(target):

    logging.debug(f"job_ag_create_job called : {target}")

    # The reason 5 secs are added : when job runs immediately, the transaction triggered the job may not be committed yet.
    start_date = target.time_to_exe if target.time_to_exe else datetime.now() + timedelta(seconds=10)
    end_date = target.time_to_stop if target.time_to_stop else None

    if target.periodic_type.name in ('IMMEDIATE', 'ONETIME'):
        dynamic_dict = dict(trigger = 'date', run_date = start_date)

    elif target.periodic_type.name == 'PERIODIC':

        #주기작업의 다음 실행 시각을 계산 : 마지막 수행시간 + 주기, 현재시간보다 과거인 경우 현재시간 적용
        last_job_start_time = getLastRundatetime(target.command_id)

        if last_job_start_time:

            param = {target.interval_type.name:target.cycle_to_exe}
            nextTime = last_job_start_time + timedelta(**param)

            if nextTime > start_date:
                start_date = nextTime

        #target.interval_type.name : minutes, hours, days
        dynamic_dict = {
            'trigger':'interval',
            'start_date':start_date,
            'end_date':end_date,
            target.interval_type.name:target.cycle_to_exe,
        }

    if target.ag_command_type.command_class == CommandClassEnum.ServerFunc:
        
        logging.debug(f"ServerFunc called : {target.ag_command_type.command_class}")

        scheduler.add_job(
                  id      ='RunBatch_'+target.command_id
                , name    = target.command_type_id
                , func    = run_batch_by_scheduler
                , args    = (target.command_id, target.ag_command_type.target_file_name, target.additional_params,)
                , **dynamic_dict
            )
    else:

        logging.debug(f"job_ag_create_job called : {target.ag_command_type.command_class}")

        scheduler.add_job(
                  id      ='CreDetail_'+target.command_id
                , name    = target.command_type_id
                , func    = createCommandDetail_bySch
                , args    = (target.command_id,)
                , **dynamic_dict
            )

#scheduler.add_job(id='job_ag_start_jobs', func=job_ag_start_jobs, trigger='date')

