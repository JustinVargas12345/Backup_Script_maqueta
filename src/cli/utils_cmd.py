import typer
import shutil
import hashlib
import tarfile
import zipfile
import logging
from pathlib import Path

import boto3
from google.cloud import storage
from azure.storage.blob import BlobServiceClient
from utils.bin_checker import check_binaries, suggest_install_instructions, find_binaries


app = typer.Typer(help="Comandos utilitarios: compresión, hash, cloud upload, paths.")


# ============================================================
# LOGGING GLOBAL
# ============================================================

LOG_PATH = Path("backup_master_log.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ============================================================
# HELPERS
# ============================================================

def ensure_dir(path: Path):
    """Crea cualquier carpeta que no exista."""
    path.mkdir(parents=True, exist_ok=True)
    logging.info(f"ensure_dir -> creada carpeta: {path}")


def generate_backup_name(db_name: str, extension: str):
    """Genera un nombre de archivo consistente."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{db_name}_{timestamp}.{extension}"
    logging.info(f"generate_backup_name -> {name}")
    return name


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
        logging.error(f"hash_file -> Archivo no encontrado: {file_path}")
        raise typer.Exit()

    if method not in ["sha256", "md5"]:
        typer.secho("Método inválido.", fg="red")
        logging.error(f"hash_file -> Método inválido: {method}")
        raise typer.Exit()

    logging.info(f"hash_file -> calculando {method} para {file_path}")

    hash_object = hashlib.sha256() if method == "sha256" else hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_object.update(chunk)

    digest = hash_object.hexdigest()
    typer.secho(f"Hash {method}: {digest}", fg="green")

    logging.info(f"hash_file -> resultado: {digest}")


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
        logging.error(f"compress_file -> Archivo no existe: {file_path}")
        raise typer.Exit()

    logging.info(f"compress_file -> formato={format}, archivo={file_path}")

    if format == "none":
        typer.secho("No se aplicó compresión.", fg="yellow")
        logging.info(f"compress_file -> formato none, archivo sin cambios.")
        return str(file_path)

    out_path = None

    if format == "zip":
        out_path = file_path.with_suffix(".zip")
        try:
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, arcname=file_path.name)
        except Exception as e:
            logging.exception("compress_file ZIP -> error")
            typer.secho(f"Error al comprimir: {e}", fg="red")
            raise typer.Exit()

    elif format == "tar.gz":
        out_path = file_path.with_suffix(".tar.gz")
        try:
            with tarfile.open(out_path, "w:gz") as tar:
                tar.add(file_path, arcname=file_path.name)
        except Exception as e:
            logging.exception("compress_file TAR.GZ -> error")
            typer.secho(f"Error al comprimir: {e}", fg="red")
            raise typer.Exit()

    else:
        typer.secho("Formato inválido.", fg="red")
        logging.error(f"compress_file -> formato invalido: {format}")
        raise typer.Exit()

    typer.secho(f"Archivo comprimido: {out_path}", fg="green")
    logging.info(f"compress_file -> generado {out_path}")

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
        logging.error(f"upload_cloud -> Archivo no encontrado: {file_path}")
        raise typer.Exit()

    if provider not in ["aws", "gcp", "azure"]:
        typer.secho("Proveedor inválido.", fg="red")
        logging.error(f"upload_cloud -> proveedor invalido: {provider}")
        raise typer.Exit()

    logging.info(f"upload_cloud -> provider={provider}, bucket={bucket}, file={file_path}")

    # ---------------- AWS ----------------
    if provider == "aws":
        try:
            s3 = boto3.client("s3")
            s3.upload_file(str(file_path), bucket, destination or file_path.name)
            typer.secho("✔ Subido a AWS S3", fg="green")
            logging.info("upload_cloud -> AWS OK")
        except Exception as e:
            logging.exception("upload_cloud -> AWS error")
            typer.secho(f"Error AWS: {e}", fg="red")

    # ---------------- GCP ----------------
    elif provider == "gcp":
        try:
            client = storage.Client()
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(destination or file_path.name)
            blob.upload_from_filename(str(file_path))
            typer.secho("✔ Subido a Google Cloud Storage", fg="green")
            logging.info("upload_cloud -> GCP OK")
        except Exception as e:
            logging.exception("upload_cloud -> GCP error")
            typer.secho(f"Error GCP: {e}", fg="red")

    # ---------------- AZURE ----------------
    elif provider == "azure":
        try:
            conn_string = typer.prompt("Azure Connection String")
            conn = BlobServiceClient.from_connection_string(conn_string)
            blob_client = conn.get_blob_client(container=bucket, blob=destination or file_path.name)

            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            typer.secho("✔ Subido a Azure Blob Storage", fg="green")
            logging.info("upload_cloud -> Azure OK")
        except Exception as e:
            logging.exception("upload_cloud -> Azure error")
            typer.secho(f"Error Azure: {e}", fg="red")


# ============================================================
# GET SIZE
# ============================================================

@app.command("size")
def get_size(file_path: str):
    """Muestra el tamaño del archivo en MB."""

    file_path = Path(file_path)

    if not file_path.exists():
        typer.secho("Archivo no encontrado.", fg="red")
        logging.error(f"get_size -> Archivo no encontrado: {file_path}")
        raise typer.Exit()

    size_mb = file_path.stat().st_size / (1024 * 1024)
    typer.secho(f"Tamaño: {size_mb:.2f} MB", fg="blue")

    logging.info(f"get_size -> {file_path} tamaño {size_mb:.2f} MB")


@app.command("check-binaries")
def cli_check_binaries():
    """Chequea la presencia de binarios externos necesarios y muestra sugerencias."""
    found = find_binaries()
    missing = [k for k, v in found.items() if not v]

    for k, v in found.items():
        if v:
            typer.echo(f"{k}: ✔ -> {v}")
        else:
            typer.echo(f"{k}: ✖")

    if missing:
        typer.secho("\nFaltan binarios. Sugerencias de instalación:", fg=typer.colors.YELLOW)
        suggestions = suggest_install_instructions()
        for m in missing:
            sugg = suggestions.get(m, "Ver documentación de instalación")
            typer.echo(f"- {m}: {sugg}")
        raise typer.Exit(code=2)
    else:
        typer.secho("Todos los binarios requeridos están presentes.", fg=typer.colors.GREEN)
