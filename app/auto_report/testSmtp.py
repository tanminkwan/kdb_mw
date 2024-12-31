import smtplib
import base64
from os.path import basename
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import COMMASPACE, formatdate, formataddr
from email.header import Header

def send_kdbMail(host, port, sender, sender_name, receivers, subject, content, files, file_names=[], cc=[], id_64='', pw_64=''):

    msg = MIMEMultipart()
    #msg = MIMEText('본문입니다.')
    msg['Subject'] = subject
    msg['From'] = formataddr((str(Header(sender_name,'utf-8')),sender))
    msg['To'] = COMMASPACE.join(receivers)
    msg['Cc'] = COMMASPACE.join(cc)
    msg['Date'] = formatdate(localtime=True)
    msg.attach(MIMEText(content, 'html'))

    file_names = [ basename(f) for f in files] if not file_names else file_names
    print('file_names : ', file_names)
    for f, fn in zip(files or [], file_names or []):
        with open(f, "rb") as fil:
            part = MIMEApplication(fil.read(), Name=fn)
        part.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', fn))
        #part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f).encode('utf-8')
        msg.attach(part)

    s = smtplib.SMTP(host,port)
    #s = smtplib.SMTP('gwe.kdb.co.kr',50025)
    s.ehlo()

    if id:
        s.docmd('auth', 'login')
        s.docmd(id_64)
        s.docmd(pw_64)

    s.sendmail(sender, receivers, msg.as_string())
    s.quit()

if __name__ == "__main__":

    id = b'o2000988@gwe.kdb.co.kr'
    id_64 = base64.encodebytes(id)
    pw = b'1q2w3e4r5t!!'
    pw_64 = base64.encodebytes(pw)

    files = ["C:\\Users\\KDB\\Downloads\\미들웨어일일점검_2021.10.01.xlsx"
            ,"C:\\Users\\KDB\\Downloads\\일일 점검결과_20211001.hwp"
            ,"C:\\Users\\KDB\\Downloads\\시스템 작업 보고_20211001.hwp"
            ]

    sender = 'o2000988@gwe.kdb.co.kr'
    sender_name = '김형기'
    subject = 'MW 일일점검(2021.09.29)'
    receivers = ['o2000988@gwe.kdb.co.kr','o2000990@gwe.kdb.co.kr','o2000689@gwe.kdb.co.kr']
    content = """
    <p style="font-family: 맑은 고딕; font-size: 12pt;">MW 일일점검 결과 보고 드립니다.</p>
    <br>
    <p style="font-family: 굴림; font-size: 12pt;">■ 일일점검 결과</p>
    <p style="font-family: 굴림; font-size: 10pt;">- 특이사항 없음</p>
    <p style="font-family: 굴림; font-size: 12pt;">■ 금일 예정 작업</p>
    <p style="font-family: 굴림; font-size: 10pt;">- 없음</p>

    """
    send_kdbMail('gwe.kdb.co.kr',50025, sender, sender_name, receivers, subject, content, files)