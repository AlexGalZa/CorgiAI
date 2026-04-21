import boto3
from django.conf import settings

from common.utils import generate_uuid
from s3.schemas import UploadFileInput


class S3Service:
    @staticmethod
    def get_client():
        if settings.S3_ACCESS_KEY_ID and settings.S3_SECRET_ACCESS_KEY:
            return boto3.client(
                "s3",
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION,
            )
        return boto3.client("s3", region_name=settings.S3_REGION)

    @staticmethod
    def upload_file(input: UploadFileInput) -> dict[str, str] | None:
        extension = ""
        if input.original_filename and "." in input.original_filename:
            extension = "." + input.original_filename.rsplit(".", 1)[-1].lower()

        s3_key = f"{input.path_prefix}/{generate_uuid()}{extension}"

        try:
            s3_client = S3Service.get_client()
            bucket_name = settings.S3_BUCKET_NAME

            extra_args: dict[str, str] = {}
            if input.content_type:
                extra_args["ContentType"] = input.content_type

            s3_client.upload_fileobj(
                input.file,
                bucket_name,
                s3_key,
                ExtraArgs=extra_args if extra_args else None,
            )

            s3_url = (
                f"https://{bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/{s3_key}"
            )

            return {"s3_key": s3_key, "s3_url": s3_url}

        except Exception:
            return None

    @staticmethod
    def generate_presigned_url(s3_key: str, expiration: int = 300) -> str | None:
        try:
            s3_client = S3Service.get_client()
            bucket_name = settings.S3_BUCKET_NAME

            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except Exception:
            return None

    @staticmethod
    def delete_file(s3_key: str) -> bool:
        try:
            s3_client = S3Service.get_client()
            bucket_name = settings.S3_BUCKET_NAME

            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            return True
        except Exception:
            return False

    @staticmethod
    def download_file(s3_key: str) -> bytes | None:
        """Download file from S3 and return its contents as bytes."""
        try:
            s3_client = S3Service.get_client()
            bucket_name = settings.S3_BUCKET_NAME

            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            return response["Body"].read()
        except Exception:
            return None
