import logging
import os

from flask.globals import _request_ctx_stack
from flask_appbuilder.filemanager import FileManager, uuid_namegen
from flask_appbuilder.upload import FileUploadField
from minio import Minio

try:
    from flask import _app_ctx_stack
except ImportError:
    _app_ctx_stack = None

app_stack = _app_ctx_stack or _request_ctx_stack

log = logging.getLogger(__name__)


class MinIOFileUploadField(FileUploadField):
    """File upload field for MinIO"""

    def __init__(self, label=None, validators=None,
                 filemanager=None,
                 **kwargs):
        """
            Constructor.

            :param label:
                Display label
            :param validators:
                Validators
        """
        super(MinIOFileUploadField, self).__init__(label, validators, **kwargs)

        if filemanager is not None:
            self.filemanager = filemanager()
        else:
            self.filemanager = FileManager()
        self._should_delete = False


class MinIOFileManager(FileManager):
    """File upload to MinIO"""

    def __init__(self,
                 bucket_name=None,
                 relative_path='',
                 namegen=None,
                 allowed_extensions=None,
                 **kwargs):

        ctx = app_stack.top

        if "MINIO_ACCESS_KEY" in ctx.app.config:
            self.minio_access_key = ctx.app.config["MINIO_ACCESS_KEY"]
        else:
            raise Exception('Config key MINIO_ACCESS_KEY is mandatory')
        if "MINIO_SECRET_KEY" in ctx.app.config:
            self.minio_secret_key = ctx.app.config["MINIO_SECRET_KEY"]
        else:
            raise Exception('Config key MINIO_SECRET_KEY is mandatory')

        if 'BUCKET_NAME' in ctx.app.config and not bucket_name:
            bucket_name = ctx.app.config['BUCKET_NAME']
        if not bucket_name:
            raise Exception('Config key BUCKET_NAME is mandatory')
        if 'BUCKET_PREFIX' in ctx.app.config and not relative_path:
            relative_path = ctx.app.config['BUCKET_PREFIX']

        self.bucket_name = bucket_name
        self.relative_path = relative_path
        self.namegen = namegen or uuid_namegen
        if not allowed_extensions and 'FILE_ALLOWED_EXTENSIONS' in ctx.app.config:
            self.allowed_extensions = ctx.app.config['FILE_ALLOWED_EXTENSIONS']
        else:
            self.allowed_extensions = allowed_extensions
        self._should_delete = False

    def get_minio_client(self):
        minio_client = Minio(
            endpoint=ctx.app.config["MINIO_ENDPOINT"],
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=ctx.app.config.get("MINIO_SECURE", True)
        )
        return minio_client

    def delete_file(self, filename):
        client = self.get_minio_client()
        file_path = os.path.join(self.relative_path, filename)
        client.remove_object(self.bucket_name, file_path)

    def save_file(self, data, filename):
        client = self.get_minio_client()
        file_path = os.path.join(self.relative_path, filename)
        client.put_object(self.bucket_name, file_path, data, len(data))
        return filename

    def get_file(self, filename):
        client = self.get_minio_client()
        file_path = os.path.join(self.relative_path, filename)
        response = client.get_object(self.bucket_name, file_path)
        body = response.read()
        response.close()
        response.release_conn()
        return body


class FileUploadView(ModelView):
    datamodel = SQLAInterface(FileManage)

    list_columns = ['filename']

    edit_form_extra_fields = add_form_extra_fields = {
        "filename": MinIOFileUploadField("MinIO File",
                                         description="",
                                         filemanager=MinIOFileManager,
                                         )
    }

    def pre_delete(self, rel_obj):
        filename = getattr(rel_obj, 'filename')
        file_obj = MinIOFileManager()
        file_obj.delete_file(filename)
