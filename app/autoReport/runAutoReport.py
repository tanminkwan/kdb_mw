from datetime import datetime, timedelta
from .testGetWasStatus import getAccessToken, getWasStatus, getNotRunningWasList
from .testXlsx import createDailyCheckXlsx
from .testSelenium import getTasks
from .testHwp2 import recreateHwp
from .testSmtp import send_kdbMail

def runAutoReport(sender, sender_name, receivers, ccs, daygap=0, was_check=True):

    print('HERE!!!')
    now = datetime.now() + timedelta(days=daygap)


    WORKING_DIR = 'C:\\mw-manager\\venv\\mw_app\\app\\autoReport\\'
    #WORKING_DIR = 'D:\\python3\\workspace\\mw-pjt\\venv\\Scripts\\first_app\\app\\autoReport\\'

    t_was_status = ''
    t_task = ''
    t_dayoff = ''
    ###########################################################################
    #1. Get current was status from 리발소
    ###########################################################################
    id = 'agent'
    pw = '1q2w3e4r!!'

    url = 'http://10.0.20.116:5000'
    login_uri = '/api/v1/security/login'
    api_uri = '/api/v1/grid/table/was_status?eql__landscape=PROD'

    rtn, access_token = getAccessToken(url+login_uri, id, pw)

    result = []
    if rtn == 1:

        rtn, was_status_l = getWasStatus(url+api_uri, access_token)

    if rtn == 1 and was_check:

        result, _ = getNotRunningWasList(was_status_l)
        print(result)

    ###########################################################################
    #2. Create Daily WAS status Report Excel file
    ###########################################################################

    ymd1 = now.strftime("%Y.%m.%d")
    master_file_name1 = WORKING_DIR + '미들웨어일일점검_template.xlsx'
    new_file_name1 = WORKING_DIR + '미들웨어일일점검_'+ymd1+'.xlsx'

    rtn, t_was_status = createDailyCheckXlsx(master_file_name1, new_file_name1, result, now)

    if rtn < 1:
        print('Excel 쓰기 권한 오류')

    ###########################################################################
    #3. Get Dayoff & Tasks  from OpenPMS
    ###########################################################################

    url_openpms = 'http://10.1.10.101:8080/openpms/'
    login_id = 'tiffanie.kim'
    login_pw = '1q2w3e4r5t!!'

    chks = [2, 5]
    persons = ['김형기','최용타','강인모','윤연상','허재영']

    tasks, dayoffs = getTasks(url_openpms, login_id, login_pw, chks, persons, now)

    t_task = '\n\n'.join([ t['content'] for t in tasks ])
    t_raw_task = '<br>'.join([ t['raw_content'] for t in tasks ])
    t_dayoff = ', '.join([ d['content'] for d in dayoffs ])

    print(t_task, t_dayoff)

    ###########################################################################
    #4. Create HWP reports
    ###########################################################################
    ymd2 = now.strftime("%Y%m%d")

    #일일 점검결과
    master_file_name2 = WORKING_DIR + '일일 점검결과_template.hwp'
    new_file_name2 = WORKING_DIR + '일일 점검결과'+'_'+ymd2+'.hwp'

    replace_text_list=[
        ('<<date>>',now.strftime("%Y.%m.%d")[2:]),
        ('<<description>>', t_was_status),
        ('<<vacation>>',t_dayoff),
        ('<<education>>',''),
    ]

    recreateHwp(master_file_name2, new_file_name2, replace_text_list)

    #시스템 작업 보고
    master_file_name3 = WORKING_DIR + '시스템 작업 보고_template.hwp'
    new_file_name3 = WORKING_DIR + '시스템 작업 보고'+'_'+ymd2+'.hwp'

    replace_text_list=[
        ('<<date>>',now.strftime("%m/%d")),
        ('<<description>>', t_task if t_task else '- 없음')
    ]

    recreateHwp(master_file_name3, new_file_name3, replace_text_list)

    ###########################################################################
    #5. Send Report e-mail
    ###########################################################################
    smtp_host = '10.6.20.40'
    smtp_port = 50025

    #sender = 'o2000988@gwe.kdb.co.kr'
    #sender_name = '김형기'
    #receivers = ['o2000988@gwe.kdb.co.kr','o2000990@gwe.kdb.co.kr','o2000689@gwe.kdb.co.kr','o1404902@gwe.kdb.co.kr']
    #cc = ['o2000866@gwe.kdb.co.kr']
    sender = sender
    sender_name = sender_name
    subject = '[리발소 일일보고 자동 발송] MW 일일점검('+ ymd1 +')'
    receivers = receivers
    cc = ccs
    #receivers = ['o2000988@gwe.kdb.co.kr']
    content = """
    <p style="color: rgb(51, 51, 51); font-family: Dotum, sans-serif, Arial, Gulim, Verdana, 'MS Gothic'; font-size: 9pt;">MW 일일점검 결과 보고 드립니다.</p>
    <br>
    <p style="margin: 0px; padding: 0px; line-height: 1.5;">■ 일일점검 결과</p>
    <p style="margin: 0px; padding: 0px; line-height: 1.5;"> %s </p>
    <br>
    <p style="margin: 0px; padding: 0px; line-height: 1.5;">■ 금일 예정 작업</p>
    <p style="margin: 0px; padding: 0px; line-height: 1.5;"> %s </p>
    <br>
    <p style="margin: 0px; padding: 0px; line-height: 1.5;">■ 금일 휴가자</p>
    <p style="margin: 0px; padding: 0px; line-height: 1.5;"> %s </p>
    """ % (t_was_status if t_was_status else '- 특이사항 없음' 
    , t_raw_task if t_raw_task else '- 없음'
    , t_dayoff if t_dayoff else '- 없음')
    files = [new_file_name3, new_file_name2, new_file_name1]

    #send_kdbMail('gwe.kdb.co.kr', 50025, sender, sender_name, receivers, subject, content, files)
    send_kdbMail(smtp_host, smtp_port, sender, sender_name, receivers, subject, content, files, cc=cc)