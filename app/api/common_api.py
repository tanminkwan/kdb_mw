from app import appbuilder
from flask import jsonify, send_file, request, current_app
from flask_appbuilder import has_access
from flask_appbuilder.api import BaseApi, expose
from app.file_manager.s3.filemanager import S3FileManager
from app.file_manager.s3.s3 import S3Client
from io import BytesIO
from app.mail_sender import send_mail

class CommonApi(BaseApi):

    route_base = '/common'

    @expose('/health', methods=['GET'])
    def health(self):
        return jsonify(status="healthy"), 200

    @expose('/download/<filename>', methods=['GET'])
    @has_access
    def download_file(self, filename):
        file_manager = S3FileManager()
        file_data = file_manager.get_file(filename)

        real_filename = filename if "_sep_" not in filename else filename.split("_sep_", 1)[1]
        return send_file(BytesIO(file_data), download_name=real_filename, as_attachment=True)

    @expose('/get_url_to_download/<filename>', methods=['GET'])
    @has_access
    def get_url_to_download(self, filename):
        file_manager = S3Client()
        download_url = file_manager.generate_presigned_url(filename, expiration=300)
        return {"download_url":download_url}

from flask_appbuilder.api import BaseApi, expose, protect

class EmailApi(BaseApi):
    resource_name = 'email'

    @expose('/send', methods=['POST'])
    def send(self):
        """이메일 발송 API
        ---
        post:
          summary: 이메일 발송
          description: SMTP를 통해 HTML 이메일을 발송합니다. (인증 불필요 - Open API)
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    sender_name:
                      type: string
                      description: 발신인 표시 이름
                      example: "리발소 시스템"
                    receivers:
                      type: string
                      description: 수신인 이메일 주소 (여러 명일 경우 콤마로 구분)
                      example: "user1@example.com, user2@example.com"
                    subject:
                      type: string
                      description: 메일 제목
                      example: "[알림] 시스템 정기 점검 안내"
                    content:
                      type: string
                      description: 메일 본문 (HTML 지원)
                      example: "<h1>공지</h1><p>내용입니다.</p>"
          responses:
            200:
              description: 발송 성공
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
                        example: "Email sent successfully"
            400:
              description: 필수 파라미터 누락
            500:
              description: 메일 발송 오류
        """
        data = request.json or {}
        sender_name = data.get('sender_name')
        receivers = data.get('receivers')
        subject = data.get('subject')
        content = data.get('content')

        if not all([sender_name, receivers, subject, content]):
            return jsonify({"error": "Missing required parameters"}), 400

        if isinstance(receivers, str):
            receivers = [r.strip() for r in receivers.split(',')]

        success, message = send_mail(
            host=current_app.config['KDB_SMTP_IP'],
            port=current_app.config['KDB_SMTP_PORT'],
            sender='admin@leebalso.org',
            sender_name=sender_name,
            receivers=receivers,
            subject=subject,
            content=content,
            use_tls=current_app.config.get('SMTP_USE_TLS', False),
            username=current_app.config.get('SMTP_USERNAME'),
            password=current_app.config.get('SMTP_PASSWORD')
        )

        if success:
            return jsonify({"message": "Email sent successfully"}), 200
        else:
            return jsonify({"error": message}), 500

appbuilder.add_api(CommonApi)
appbuilder.add_api(EmailApi)
