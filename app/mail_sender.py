"""
Mail Sender Module
- SMTP를 통한 HTML 이메일 발송
- Gmail / 사내 SMTP 모두 지원
- 파일 첨부 및 본문 삽입 이미지(CID) 지원
- UTF-8 한글 파일명 지원
"""
import smtplib
import logging
from os.path import basename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.utils import COMMASPACE, formatdate, formataddr
from email.header import Header

log = logging.getLogger(__name__)


def send_mail(host, port, sender, sender_name, receivers, subject, content,
              files=None, cc=None, content_type='html',
              use_tls=False, username=None, password=None,
              inline_images=None):
    """
    SMTP를 통해 이메일을 발송합니다.

    Args:
        host (str): SMTP 서버 주소 (예: 'smtp.gmail.com')
        port (int): SMTP 포트 (Gmail: 587)
        sender (str): 발신자 이메일 주소
        sender_name (str): 발신자 표시 이름
        receivers (list): 수신자 이메일 주소 목록
        subject (str): 이메일 제목
        content (str): 이메일 본문 (HTML 또는 plain text)
        files (list, optional): 첨부파일 목록 (경로 또는 (파일명, 바이트) 튜플)
        cc (list, optional): 참조 이메일 주소 목록
        content_type (str): 본문 타입 ('html' 또는 'plain')
        use_tls (bool): TLS 사용 여부 (Gmail은 True)
        username (str, optional): SMTP 인증 사용자명
        password (str, optional): SMTP 인증 비밀번호
        inline_images (list, optional): 본문 삽입용 이미지 목록 [(cid, content), ...]

    Returns:
        tuple: (success: bool, message: str)
    """
    files = files or []
    cc = cc or []
    inline_images = inline_images or []

    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = formataddr((str(Header(sender_name, 'utf-8')), sender))
        msg['To'] = COMMASPACE.join(receivers)
        msg['Cc'] = COMMASPACE.join(cc)
        msg['Date'] = formatdate(localtime=True)
        
        # 본문 연결
        msg.attach(MIMEText(content, content_type, 'utf-8'))

        # 본문 삽입용 이미지 처리 (CID)
        for cid, img_content in inline_images:
            try:
                img = MIMEImage(img_content)
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=cid)
                msg.attach(img)
            except Exception as e:
                log.warning(f"Inline image attachment failed for CID {cid}: {e}")

        # 파일 첨부
        for entry in files:
            try:
                if isinstance(entry, tuple):
                    fn, file_content = entry
                else:
                    fn = basename(entry)
                    with open(entry, "rb") as fil:
                        file_content = fil.read()
                
                part = MIMEApplication(file_content, Name=fn)
                part.add_header('Content-Disposition', 'attachment',
                                filename=('utf-8', '', fn))
                msg.attach(part)
            except Exception as e:
                log.warning(f"Attachment failed for {entry}: {e}")
                continue

        # SMTP 전송
        all_recipients = receivers + cc
        s = smtplib.SMTP(host, port)
        s.ehlo()

        if use_tls:
            s.starttls()
            s.ehlo()

        if username and password:
            s.login(username, password)

        s.sendmail(sender, all_recipients, msg.as_string())
        s.quit()

        log.info(f"Email sent successfully: subject='{subject}', to={receivers}")
        return True, 'OK'

    except Exception as e:
        log.error(f"Email send failed: {e}")
        return False, str(e)
