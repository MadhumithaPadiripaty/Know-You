import boto3
import os
import uuid

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

BUCKET = os.getenv("S3_BUCKET")


def upload_bytes(data: bytes):
    key = f"chunks/{uuid.uuid4()}.csv"
    s3.put_object(Bucket=BUCKET, Key=key, Body=data)
    return key


def download_bytes(key: str):
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return obj["Body"].read()
