'''
import logging
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class CloudStorage:
    """
    Maneja el almacenamiento en la nube (AWS S3, GCP, Azure).

    Implementación robusta con:
    - Validación de configuración
    - Soporte por URL/env/config dict
    - Reintentos con backoff
    - Importación perezosa de SDKs
    """

    def __init__(self, provider: str, config: Optional[Dict[str, Any]] = None,
                 retries: int = 3, backoff: float = 1.0, timeout: int = 60):
        self.provider = (provider or "").lower()
        self.config = config or {}
        self.retries = int(retries)
        self.backoff = float(backoff)
        self.timeout = int(timeout)

        if not self.provider:
            raise ValueError("Provider inválido (vacío). Usa: 'aws', 'gcp' o 'azure'.")
        if self.provider not in ("aws", "gcp", "azure"):
            raise ValueError("Proveedor inválido. Debe ser: 'aws', 'gcp' o 'azure'.")

        self._normalize_config()
        self._client = None

    def _normalize_config(self):
        url = self.config.get("url") or os.environ.get(self.config.get("env_url", ""))
        if url:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            if scheme in ("s3", "gs", "gcs", "azure"):
                name = parsed.netloc or parsed.path.lstrip("/")
                if scheme == "s3":
                    self.provider = "aws"
                    self.config.setdefault("bucket", name)
                    qs = parse_qs(parsed.query)
                    if qs.get("region"):
                        self.config.setdefault("region", qs.get("region")[0])
                elif scheme in ("gs", "gcs"):
                    self.provider = "gcp"
                    self.config.setdefault("bucket", name)
                elif scheme == "azure":
                    self.provider = "azure"
                    self.config.setdefault("container", name)

        env_prefix = self.config.get("env_prefix")
        if env_prefix:
            for key in ("bucket", "region", "aws_access_key", "aws_secret_key", "container", "connection_string", "service_account_file"):
                if key not in self.config:
                    val = os.environ.get(f"{env_prefix}_{key.upper()}")
                    if val:
                        self.config[key] = val

    def _ensure_client(self):
        if self._client is None:
            self._client = self._connect()
        return self._client

    def _retry(self, fn, *args, **kwargs):
        last_exc = None
        delay = self.backoff
        for attempt in range(1, self.retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                logger.debug("CloudStorage attempt %s/%s failed: %s", attempt, self.retries, e)
                if attempt == self.retries:
                    break
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Operación de CloudStorage falló tras {self.retries} intentos: {last_exc}") from last_exc

    def _connect(self):
        try:
            if self.provider == "aws":
                try:
                    import boto3
                except Exception as e:
                    raise RuntimeError("Falta la librería 'boto3'. Instálala: pip install boto3") from e
                return boto3.client(
                    "s3",
                    aws_access_key_id=self.config.get("aws_access_key") or self.config.get("access_key"),
                    aws_secret_access_key=self.config.get("aws_secret_key") or self.config.get("secret_key"),
                    region_name=self.config.get("region")
                )

            elif self.provider == "gcp":
                try:
                    from google.cloud import storage as gcs_storage
                except Exception as e:
                    raise RuntimeError("Falta la librería 'google-cloud-storage'. Instálala: pip install google-cloud-storage") from e
                sa_file = self.config.get("service_account_file")
                if sa_file and not Path(sa_file).exists():
                    raise FileNotFoundError(f"Archivo service_account_file inválido: {sa_file}")
                if sa_file:
                    return gcs_storage.Client.from_service_account_json(sa_file)
                return gcs_storage.Client()

            elif self.provider == "azure":
                try:
                    from azure.storage.blob import BlobServiceClient
                except Exception as e:
                    raise RuntimeError("Falta la librería 'azure-storage-blob'. Instálala: pip install azure-storage-blob") from e
                conn = self.config.get("connection_string")
                if not conn:
                    raise ValueError("Se requiere 'connection_string' para Azure Blob Storage.")
                return BlobServiceClient.from_connection_string(conn)

        except Exception as e:
            raise RuntimeError(f"Error al conectar a {self.provider}: {e}") from e

    def save_file(self, src_path: str, dest_name: Optional[str] = None) -> Dict[str, Any]:
        file = Path(src_path)
        if not file.exists():
            raise FileNotFoundError(f"Archivo local '{src_path}' no existe.")
        remote_name = dest_name or file.name

        def _do_upload():
            client = self._ensure_client()
            if self.provider == "aws":
                bucket = self.config.get("bucket")
                if not bucket:
                    raise ValueError("Falta 'bucket' en la configuración para AWS S3.")
                client.upload_file(Filename=str(file), Bucket=bucket, Key=remote_name)
            elif self.provider == "gcp":
                bucket_name = self.config.get("bucket")
                if not bucket_name:
                    raise ValueError("Falta 'bucket' en la configuración para GCP.")
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(remote_name)
                blob.upload_from_filename(str(file))
            elif self.provider == "azure":
                container = self.config.get("container")
                if not container:
                    raise ValueError("Falta 'container' en la configuración para Azure.")
                container_client = client.get_container_client(container)
                blob_client = container_client.get_blob_client(remote_name)
                with open(file, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
            return {"provider": self.provider, "bucket": self.config.get("bucket") or self.config.get("container"), "key": remote_name}

        return self._retry(_do_upload)

    def get_path(self, file_name: str, local_dest: Optional[str] = None) -> str:
        local_path = Path(local_dest or file_name)
        if local_path.parent and not local_path.parent.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)

        def _do_download():
            client = self._ensure_client()
            if self.provider == "aws":
                bucket = self.config.get("bucket")
                client.download_file(bucket, file_name, str(local_path))
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                blob = bucket.blob(file_name)
                blob.download_to_filename(str(local_path))
            elif self.provider == "azure":
                container_client = client.get_container_client(self.config.get("container"))
                blob = container_client.get_blob_client(file_name)
                data = blob.download_blob().readall()
                local_path.write_bytes(data)
            return str(local_path)

        return self._retry(_do_download)

    def delete_file(self, file_name: str) -> bool:
        def _do_delete():
            client = self._ensure_client()
            if self.provider == "aws":
                client.delete_object(Bucket=self.config.get("bucket"), Key=file_name)
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                bucket.blob(file_name).delete()
            elif self.provider == "azure":
                container_client = client.get_container_client(self.config.get("container"))
                container_client.get_blob_client(file_name).delete_blob()
            return True

        try:
            return self._retry(_do_delete)
        except Exception as e:
            logger.warning("delete_file failed: %s", e)
            return False

    def list_files(self) -> List[str]:
        def _do_list():
            client = self._ensure_client()
            if self.provider == "aws":
                result = client.list_objects_v2(Bucket=self.config.get("bucket"))
                return [obj["Key"] for obj in result.get("Contents", [])]
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                return [blob.name for blob in bucket.list_blobs()]
            elif self.provider == "azure":
                container_client = client.get_container_client(self.config.get("container"))
                return [blob.name for blob in container_client.list_blobs()]

        return self._retry(_do_list)

*** End Patch
'''