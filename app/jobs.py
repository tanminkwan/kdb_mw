from . import db, scheduler
from datetime import datetime, timedelta
from sqlalchemy.sql import select, update
from app.models.agent import AgCommandType, AgCommandMaster, AgCommandDetail\
    , AgResult, AgAgentGroup, AgAgent
from app.sqls.agent import finishCommands_bySch, createCommandDetail_bySch\
    , get_commands, getCloseToTokenExpiry_bySch, getLastRundatetime
from app.sqls.batch import runBatch_bySch

@scheduler.task('cron', id='job_ag_finish_commands', name='Remove Finished Commands', minute='*/1')
def job_ag_finish_commands():
    #print(datetime.now(),'test_job1 is invoked!!')
    #stmt = select([AgCommandMaster]).where(AgCommandType.command_type_id=='READHTTPM')
    #command_type_rec = db.session.execute(stmt).fetchone()
    finishCommands_bySch()

    #print(command_type_rec)

#@scheduler.task('cron', id='job_ag_closeToTokenExpiry', second='*/30')
@scheduler.task('cron', id='job_ag_extend_token_expiry', name='Refrash Token Update to Agents', hour='*/12')
def job_ag_extend_token_expiry():
    getCloseToTokenExpiry_bySch(3)

#@scheduler.task('date', id='job_ag_start_jobs')
def job_ag_start_jobs():
    print(datetime.now(),'job_ag_start_jobs is invoked!!')

    commands = get_commands()
    
    for cmd in commands:
        job_ag_create_job(cmd)

def job_ag_create_job(target):

    print('job_ag_create_job Started!')
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
        dynamic_dict = {'trigger':'interval'
                       ,'start_date':start_date
                       ,'end_date':end_date
                       ,target.interval_type.name:target.cycle_to_exe}

    if target.ag_command_type.command_class.name == 'ServerFunc':
        
        scheduler.add_job(
                  id      ='RunBatch_'+target.command_id
                , name    = target.command_type_id
                , func    = runBatch_bySch
                , args    = (target.command_id, target.ag_command_type.target_file_name, target.ag_command_type.target_file_path, target.additional_params,)
                , **dynamic_dict
            )
    else:
        scheduler.add_job(
                  id      ='CreDetail_'+target.command_id
                , name    = target.command_type_id
                , func    = createCommandDetail_bySch
                , args    = (target.command_id,)
                , **dynamic_dict
            )

scheduler.add_job(id='job_ag_start_jobs', func=job_ag_start_jobs, trigger='date')

