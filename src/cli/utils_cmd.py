import typer
import shutil
import hashlib
import tarfile
import zipfile
from pathlib import Path

import boto3
from google.cloud import storage
from azure.storage.blob import BlobServiceClient


app = typer.Typer(help="Comandos utilitarios: compresión, hash, cloud upload, paths.")


# ============================================================
# HELPERS
# ============================================================

def ensure_dir(path: Path):
    """Crea cualquier carpeta que no exista."""
    path.mkdir(parents=True, exist_ok=True)


def generate_backup_name(db_name: str, extension: str):
    """Genera un nombre de archivo consistente."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{db_name}_{timestamp}.{extension}"


# ============================================================
# HASHING
# ============================================================

@app.command("hash")
def hash_file(
    file_path: str = typer.Argument(..., help="Ruta del archivo."),
    method: str = typer.Option("sha256", help="sha256 | md5")
):
    """Calcula el hash de un archivo."""

    file_path = Path(file_path)
    if not file_path.exists():
        typer.secho("Archivo no encontrado.", fg="red")
        raise typer.Exit()

    if method not in ["sha256", "md5"]:
        typer.secho("Método inválido.", fg="red")
        raise typer.Exit()

    hash_object = hashlib.sha256() if method == "sha256" else hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_object.update(chunk)

    typer.secho(f"Hash {method}: {hash_object.hexdigest()}", fg="green")


# ============================================================
# COMPRESIÓN
# ============================================================

@app.command("compress")
def compress_file(
    file_path: str = typer.Argument(..., help="Archivo a comprimir"),
    format: str = typer.Option("zip", help="zip | tar.gz | none")
):
    """Comprime un archivo en ZIP o TAR.GZ."""

    file_path = Path(file_path)

    if not file_path.exists():
        typer.secho("Archivo no existe.", fg="red")
        raise typer.Exit()

    if format == "none":
        typer.secho("No se aplicó compresión.", fg="yellow")
        return str(file_path)

    out_path = None

    if format == "zip":
        out_path = file_path.with_suffix(".zip")
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, arcname=file_path.name)

    elif format == "tar.gz":
        out_path = file_path.with_suffix(".tar.gz")
        with tarfile.open(out_path, "w:gz") as tar:
            tar.add(file_path, arcname=file_path.name)

    else:
        typer.secho("Formato inválido.", fg="red")
        raise typer.Exit()

    typer.secho(f"Archivo comprimido: {out_path}", fg="green")
    return str(out_path)


# ============================================================
# UPLOAD TO CLOUD
# ============================================================

@app.command("upload")
def upload_cloud(
    file_path: str = typer.Argument(..., help="Archivo a subir"),
    provider: str = typer.Option(..., help="aws | gcp | azure"),
    bucket: str = typer.Option(..., help="Nombre del bucket"),
    destination: str = typer.Option("", help="Ruta remota dentro del bucket")
):
    """Sube un archivo a AWS S3, Google Cloud Storage o Azure Blob."""

    file_path = Path(file_path)
    if not file_path.exists():
        typer.secho("Archivo no encontrado.", fg="red")
        raise typer.Exit()

    if provider not in ["aws", "gcp", "azure"]:
        typer.secho("Proveedor inválido.", fg="red")
        raise typer.Exit()

    # ---------------- AWS ----------------
    if provider == "aws":
        s3 = boto3.client("s3")
        s3.upload_file(str(file_path), bucket, destination or file_path.name)
        typer.secho("✔ Subido a AWS S3", fg="green")

    # ---------------- GCP ----------------
    elif provider == "gcp":
        client = storage.Client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(destination or file_path.name)
        blob.upload_from_filename(str(file_path))
        typer.secho("✔ Subido a Google Cloud Storage", fg="green")

    # ---------------- AZURE ----------------
    elif provider == "azure":
        conn = BlobServiceClient.from_connection_string(typer.prompt("Azure Connection String"))
        blob_client = conn.get_blob_client(container=bucket, blob=destination or file_path.name)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        typer.secho("✔ Subido a Azure Blob Storage", fg="green")


# ============================================================
# GET SIZE
# ============================================================

@app.command("size")
def get_size(file_path: str):
    """Muestra el tamaño del archivo en MB."""

    file_path = Path(file_path)
    if not file_path.exists():
        typer.secho("Archivo no encontrado.", fg="red")
        raise typer.Exit()

    size_mb = file_path.stat().st_size / (1024 * 1024)
    typer.secho(f"Tamaño: {size_mb:.2f} MB", fg="blue")
