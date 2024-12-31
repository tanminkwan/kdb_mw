import boto3
from botocore.client import Config
import argparse

class MinioManager:
    def __init__(self, minio_url, access_key, secret_key):
        self.s3 = boto3.client('s3',
                               endpoint_url=minio_url,
                               aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key,
                               config=Config(signature_version='s3v4'))

    def upload_file(self, bucket_name, file_name, file_path):
        try:
            self.s3.upload_file(file_path, bucket_name, file_name)
            print(f"File '{file_path}' uploaded to '{bucket_name}/{file_name}' successfully.")
        except Exception as e:
            print(f"Error uploading file: {e}")

    def download_file(self, bucket_name, file_name, download_path):
        try:
            self.s3.download_file(bucket_name, file_name, download_path)
            print(f"File '{file_name}' downloaded to '{download_path}' successfully.")
        except Exception as e:
            print(f"Error downloading file: {e}")

    def get_metadata(self, bucket_name, file_name):
        try:
            response = self.s3.head_object(Bucket=bucket_name, Key=file_name)
            print(f"Metadata for '{bucket_name}/{file_name}':")
            print(response)
        except Exception as e:
            print(f"Error retrieving metadata: {e}")

def main():
    parser = argparse.ArgumentParser(description='MinIO 파일 관리')
    parser.add_argument('bucket_file', type=str, help='<bucket-name>/<file_name>')
    parser.add_argument('operation', type=str, choices=['upload', 'download', 'meta'], help='작업 종류: upload/download/meta정보조회')
    parser.add_argument('--file-path', type=str, help='업로드할 파일의 경로 (업로드 시 필요)', default='')
    parser.add_argument('--download-path', type=str, help='다운로드할 파일의 저장 경로 (다운로드 시 필요)', default='')

    args = parser.parse_args()

    bucket_name, file_name = args.bucket_file.split('/', 1)

    # MinIO 서버 설정
    minio_url = 'http://localhost:9000'  # MinIO 서버 주소
    access_key = 'x7QobM7I5WNI5zGWbkr4'
    secret_key = 'pdoWz2Zw0yaJw9fW32jqZigaqiyXRuYLKK9x7PzJ'

    manager = MinioManager(minio_url, access_key, secret_key)
    
    if args.operation == 'upload':
        if not args.file_path:
            print("업로드할 파일의 경로를 지정해야 합니다.")
            return
        manager.upload_file(bucket_name, file_name, args.file_path)
    elif args.operation == 'download':
        if not args.download_path:
            print("다운로드할 파일의 저장 경로를 지정해야 합니다.")
            return
        manager.download_file(bucket_name, file_name, args.download_path)
    elif args.operation == 'meta':
        manager.get_metadata(bucket_name, file_name)

if __name__ == '__main__':
    main()
