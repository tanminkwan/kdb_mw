from app import appbuilder
from flask import jsonify, send_file
from flask_appbuilder import has_access
from flask_appbuilder.api import BaseApi, expose
from app.file_manager.s3.filemanager import S3FileManager
from app.file_manager.s3.s3 import S3Client
from io import BytesIO

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

appbuilder.add_api(CommonApi)
