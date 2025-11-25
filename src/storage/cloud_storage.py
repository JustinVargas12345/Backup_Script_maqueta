import boto3
from botocore.exceptions import ClientError
from google.cloud import storage as gcs_storage
from azure.storage.blob import BlobServiceClient
from pathlib import Path
from typing import Optional


class CloudStorage:
    """
    Maneja el almacenamiento en la nube (AWS S3, GCP, Azure).
    """

    def __init__(self, provider: str, config: dict):
        self.provider = provider.lower()
        self.config = config

        if self.provider not in ("aws", "gcp", "azure"):
            raise ValueError("Proveedor inválido. Debe ser: 'aws', 'gcp' o 'azure'.")

        self._client = self._connect()

    # Conectar al proveedor
    def _connect(self):
        if self.provider == "aws":
            return boto3.client(
                "s3",
                aws_access_key_id=self.config.get("aws_access_key"),
                aws_secret_access_key=self.config.get("aws_secret_key"),
                region_name=self.config.get("region")
            )
        elif self.provider == "gcp":
            return gcs_storage.Client.from_service_account_json(
                self.config.get("service_account_file")
            )
        elif self.provider == "azure":
            return BlobServiceClient.from_connection_string(
                self.config.get("connection_string")
            )

    # Guardar archivo
    def save_file(self, src_path: str, dest_name: Optional[str] = None) -> str:
        file = Path(src_path)
        if not file.exists():
            raise FileNotFoundError(f"Archivo local '{src_path}' no existe.")
        remote_name = dest_name or file.name

        if self.provider == "aws":
            self._client.upload_file(Filename=str(file), Bucket=self.config["bucket"], Key=remote_name)
        elif self.provider == "gcp":
            bucket = self._client.bucket(self.config["bucket"])
            blob = bucket.blob(remote_name)
            blob.upload_from_filename(str(file))
        elif self.provider == "azure":
            container = self._client.get_container_client(self.config["container"])
            blob = container.get_blob_client(remote_name)
            with open(file, "rb") as data:
                blob.upload_blob(data, overwrite=True)

        return remote_name

    # Descargar archivo
    def get_path(self, file_name: str, local_dest: Optional[str] = None) -> str:
        local_path = Path(local_dest or file_name)

        if self.provider == "aws":
            self._client.download_file(self.config["bucket"], file_name, str(local_path))
        elif self.provider == "gcp":
            bucket = self._client.bucket(self.config["bucket"])
            blob = bucket.blob(file_name)
            blob.download_to_filename(str(local_path))
        elif self.provider == "azure":
            container = self._client.get_container_client(self.config["container"])
            blob = container.get_blob_client(file_name)
            data = blob.download_blob().readall()
            local_path.write_bytes(data)

        return str(local_path)

    # Borrar archivo
    def delete_file(self, file_name: str) -> bool:
        if self.provider == "aws":
            self._client.delete_object(Bucket=self.config["bucket"], Key=file_name)
        elif self.provider == "gcp":
            bucket = self._client.bucket(self.config["bucket"])
            blob = bucket.blob(file_name)
            blob.delete()
        elif self.provider == "azure":
            container = self._client.get_container_client(self.config["container"])
            blob = container.get_blob_client(file_name)
            blob.delete_blob()
        return True

    # Listar archivos
    def list_files(self) -> list[str]:
        if self.provider == "aws":
            result = self._client.list_objects_v2(Bucket=self.config["bucket"])
            return [obj["Key"] for obj in result.get("Contents", [])]
        elif self.provider == "gcp":
            bucket = self._client.bucket(self.config["bucket"])
            return [blob.name for blob in bucket.list_blobs()]
        elif self.provider == "azure":
            container = self._client.get_container_client(self.config["container"])
            return [blob.name for blob in container.list_blobs()]
