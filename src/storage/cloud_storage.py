
import logging
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class CloudStorage:
    """Clase para subir/descargar/listar/borrar objetos en S3/GCS/Azure.

    Ejemplo mínimo:
        s = CloudStorage('aws', {'bucket':'mi-bucket','aws_access_key':'..','aws_secret_key':'..'})
        s.save_file('backups/db.dump')
    """

    def __init__(self, provider: str, config: Optional[Dict[str, Any]] = None,
                 retries: int = 3, backoff: float = 1.0, timeout: int = 60):
        self.provider = (provider or "").lower()
        self.config = config or {}
        self.retries = int(retries)
        self.backoff = float(backoff)
        self.timeout = int(timeout)

        if not self.provider or self.provider not in ("aws", "gcp", "azure"):
            raise ValueError("Proveedor inválido: use 'aws', 'gcp' o 'azure'.")

        self._normalize_config()
        self._client = None

    def _normalize_config(self):
        # soporta config por URL: s3://bucket?region=eu-west-1
        url = self.config.get("url") or os.environ.get(self.config.get("env_url", ""))
        if url:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
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

        # prefijo de entorno (BACKUP_S3_BUCKET ...)
        env_prefix = self.config.get("env_prefix")
        if env_prefix:
            for key in ("bucket", "region", "aws_access_key", "aws_secret_key", "container", "connection_string", "service_account_file"):
                if key not in self.config:
                    v = os.environ.get(f"{env_prefix}_{key.upper()}")
                    if v:
                        self.config[key] = v

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
        raise RuntimeError(f"Operación fallida tras {self.retries} intentos: {last_exc}") from last_exc

    def _connect(self):
        try:
            if self.provider == "aws":
                try:
                    import boto3
                except Exception as e:
                    raise RuntimeError("Falta 'boto3'. Instálalo: pip install boto3") from e
                return boto3.client(
                    "s3",
                    aws_access_key_id=self.config.get("aws_access_key") or self.config.get("access_key"),
                    aws_secret_access_key=self.config.get("aws_secret_key") or self.config.get("secret_key"),
                    region_name=self.config.get("region")
                )

            if self.provider == "gcp":
                try:
                    from google.cloud import storage as gcs_storage
                except Exception as e:
                    raise RuntimeError("Falta 'google-cloud-storage'. Instálalo: pip install google-cloud-storage") from e
                sa = self.config.get("service_account_file")
                if sa and not Path(sa).exists():
                    raise FileNotFoundError(f"service_account_file inválido: {sa}")
                return gcs_storage.Client.from_service_account_json(sa) if sa else gcs_storage.Client()

            if self.provider == "azure":
                try:
                    from azure.storage.blob import BlobServiceClient
                except Exception as e:
                    raise RuntimeError("Falta 'azure-storage-blob'. Instálalo: pip install azure-storage-blob") from e
                conn = self.config.get("connection_string")
                if not conn:
                    raise ValueError("Se requiere 'connection_string' para Azure Blob Storage.")
                return BlobServiceClient.from_connection_string(conn)

        except Exception as e:
            raise RuntimeError(f"Error conectando a {self.provider}: {e}") from e

    # Operaciones
    def save_file(self, src_path: str, dest_name: Optional[str] = None) -> Dict[str, Any]:
        file = Path(src_path)
        if not file.exists():
            raise FileNotFoundError(f"Archivo '{src_path}' no existe")
        
        # Validar tamaño del archivo (advertencia si es muy grande)
        file_size = file.stat().st_size
        size_mb = file_size / (1024 * 1024)
        if file_size > 5 * 1024 * 1024 * 1024:  # 5GB
            logger.warning(f"Archivo grande ({size_mb:.1f} MB) será subido a {self.provider}. Puede tardar bastante.")
        
        key = dest_name or file.name

        def _upload():
            client = self._ensure_client()
            if self.provider == "aws":
                bucket = self.config.get("bucket")
                if not bucket:
                    raise ValueError("Falta 'bucket' en la configuración para AWS")
                logger.info(f"Subiendo {file.name} a S3 ({size_mb:.1f} MB)...")
                client.upload_file(str(file), bucket, key)
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                blob = bucket.blob(key)
                logger.info(f"Subiendo {file.name} a GCS ({size_mb:.1f} MB)...")
                blob.upload_from_filename(str(file))
            elif self.provider == "azure":
                container = self.config.get("container")
                container_client = client.get_container_client(container)
                blob_client = container_client.get_blob_client(key)
                logger.info(f"Subiendo {file.name} a Azure Blob ({size_mb:.1f} MB)...")
                with open(file, "rb") as f:
                    blob_client.upload_blob(f, overwrite=True)
            logger.info(f"Archivo subido exitosamente: {key}")
            return {"provider": self.provider, "bucket": self.config.get("bucket") or self.config.get("container"), "key": key}

        return self._retry(_upload)

    def get_path(self, file_name: str, local_dest: Optional[str] = None) -> str:
        local_path = Path(local_dest or file_name)
        if local_path.parent and not local_path.parent.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)

        def _download():
            client = self._ensure_client()
            logger.info(f"Descargando {file_name} desde {self.provider}...")
            if self.provider == "aws":
                client.download_file(self.config.get("bucket"), file_name, str(local_path))
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                blob = bucket.blob(file_name)
                blob.download_to_filename(str(local_path))
            elif self.provider == "azure":
                container_client = client.get_container_client(self.config.get("container"))
                blob = container_client.get_blob_client(file_name)
                data = blob.download_blob().readall()
                local_path.write_bytes(data)
            
            # Validar descarga
            if local_path.exists():
                size_mb = local_path.stat().st_size / (1024 * 1024)
                logger.info(f"Descarga completada: {file_name} ({size_mb:.1f} MB)")
            else:
                raise RuntimeError(f"Fallo descargando {file_name}: archivo no existe en destino")
            
            return str(local_path)

        return self._retry(_download)

    def delete_file(self, file_name: str) -> bool:
        def _delete():
            client = self._ensure_client()
            logger.info(f"Eliminando {file_name} desde {self.provider}...")
            if self.provider == "aws":
                client.delete_object(Bucket=self.config.get("bucket"), Key=file_name)
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                bucket.blob(file_name).delete()
            elif self.provider == "azure":
                container_client = client.get_container_client(self.config.get("container"))
                container_client.get_blob_client(file_name).delete_blob()
            logger.info(f"Archivo eliminado exitosamente: {file_name}")
            return True

        try:
            return self._retry(_delete)
        except Exception as e:
            logger.warning("delete_file failed: %s", e)
            return False

    def list_files(self) -> List[str]:
        def _list():
            client = self._ensure_client()
            logger.info(f"Listando archivos desde {self.provider}...")
            if self.provider == "aws":
                res = client.list_objects_v2(Bucket=self.config.get("bucket"))
                files = [o["Key"] for o in res.get("Contents", [])]
            elif self.provider == "gcp":
                bucket = client.bucket(self.config.get("bucket"))
                files = [b.name for b in bucket.list_blobs()]
            elif self.provider == "azure":
                container_client = client.get_container_client(self.config.get("container"))
                files = [b.name for b in container_client.list_blobs()]
            logger.info(f"Se encontraron {len(files)} archivos en {self.provider}")
            return files

        return self._retry(_list)

    @classmethod
    def from_env(cls, provider: str, env_prefix: str, **kwargs):
        cfg: Dict[str, Any] = {"env_prefix": env_prefix}
        for key in ("bucket", "region", "aws_access_key", "aws_secret_key", "container", "connection_string", "service_account_file"):
            v = os.environ.get(f"{env_prefix}_{key.upper()}")
            if v:
                cfg[key] = v
        cfg.update(kwargs)
        return cls(provider, cfg)
