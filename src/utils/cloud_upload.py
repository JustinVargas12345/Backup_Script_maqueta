import boto3
from google.cloud import storage
from azure.storage.blob import BlobServiceClient


def upload_s3(bucket: str, key: str, filepath: str,
              access_key: str, secret_key: str, region: str):

    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )

    s3 = session.client("s3")
    s3.upload_file(filepath, bucket, key)
    return f"s3://{bucket}/{key}"


def upload_gcs(bucket_name: str, blob_name: str, filepath: str,
               credentials_path: str):

    client = storage.Client.from_service_account_json(credentials_path)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(filepath)
    return f"gs://{bucket_name}/{blob_name}"


def upload_azure(container: str, blob_name: str, filepath: str,
                 connection_string: str):

    client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = client.get_blob_client(container=container, blob=blob_name)

    with open(filepath, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    return f"azure://{container}/{blob_name}"
