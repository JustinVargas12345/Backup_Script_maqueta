import boto3
from botocore.exceptions import ClientError
from google.cloud import storage as gcs_storage
from azure.storage.blob import BlobServiceClient

from pathlib import Path
from typing import Optional


class CloudStorage:
    """
    Maneja el almacenamiento en la nube para múltiples proveedores:
    - AWS S3
    - Google Cloud Storage
    - Azure Blob Storage

    provider: "aws" | "gcp" | "azure"
    config: dict con las credenciales y configuraciones necesarias.
    """

    def __init__(self, provider: str, config: dict):
        self.provider = provider.lower()

        if self.provider not in ("aws", "gcp", "azure"):
            raise ValueError("Proveedor inválido. Debe ser: 'aws', 'gcp' o 'azure'.")

        self.config = config
        self._client = self._connect()

    # ======================================================================
    # Conectar al proveedor
    # ======================================================================

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

    # ======================================================================
    # SUBIR ARCHIVO
    # ======================================================================

    def upload(self, local_path: str, remote_path: str) -> bool:
        """
        Sube un archivo a la nube.
        local_path → archivo local.
        remote_path → ruta destino en la nube.
        """

        file = Path(local_path)

        if not file.exists():
            raise FileNotFoundError(f"El archivo '{local_path}' no existe.")

        if self.provider == "aws":
            try:
                self._client.upload_file(
                    Filename=str(file),
                    Bucket=self.config["bucket"],
                    Key=remote_path
                )
                return True
            except ClientError as e:
                print("Error subiendo archivo a AWS:", e)
                return False

        elif self.provider == "gcp":
            try:
                bucket = self._client.bucket(self.config["bucket"])
                blob = bucket.blob(remote_path)
                blob.upload_from_filename(str(file))
                return True
            except Exception as e:
                print("Error subiendo archivo a GCP:", e)
                return False

        elif self.provider == "azure":
            try:
                container = self._client.get_container_client(self.config["container"])
                blob = container.get_blob_client(remote_path)
                with open(file, "rb") as data:
                    blob.upload_blob(data, overwrite=True)
                return True
            except Exception as e:
                print("Error subiendo archivo a Azure:", e)
                return False

    # ======================================================================
    # DESCARGAR ARCHIVO
    # ======================================================================

    def download(self, remote_path: str, local_path: str) -> bool:
        """
        Descarga un archivo desde la nube.
        """
        local_path = Path(local_path)

        if self.provider == "aws":
            try:
                self._client.download_file(
                    self.config["bucket"], remote_path, str(local_path)
                )
                return True
            except ClientError as e:
                print("Error descargando archivo AWS:", e)
                return False

        elif self.provider == "gcp":
            try:
                bucket = self._client.bucket(self.config["bucket"])
                blob = bucket.blob(remote_path)
                blob.download_to_filename(str(local_path))
                return True
            except Exception as e:
                print("Error descargando archivo GCP:", e)
                return False

        elif self.provider == "azure":
            try:
                container = self._client.get_container_client(self.config["container"])
                blob = container.get_blob_client(remote_path)
                data = blob.download_blob().readall()
                local_path.write_bytes(data)
                return True
            except Exception as e:
                print("Error descargando archivo Azure:", e)
                return False

    # ======================================================================
    # ELIMINAR ARCHIVO REMOTO
    # ======================================================================

    def delete(self, remote_path: str) -> bool:
        """
        Elimina un archivo en la nube.
        """

        if self.provider == "aws":
            try:
                self._client.delete_object(
                    Bucket=self.config["bucket"],
                    Key=remote_path
                )
                return True
            except ClientError:
                return False

        elif self.provider == "gcp":
            try:
                bucket = self._client.bucket(self.config["bucket"])
                blob = bucket.blob(remote_path)
                blob.delete()
                return True
            except Exception:
                return False

        elif self.provider == "azure":
            try:
                container = self._client.get_container_client(self.config["container"])
                blob = container.get_blob_client(remote_path)
                blob.delete_blob()
                return True
            except Exception:
                return False
