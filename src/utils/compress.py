import os
import tarfile
import zipfile
import shutil


def compress_file(input_path: str, output_path: str, method: str = "zip"):
    """
    Comprime un archivo o directorio en ZIP, TAR o GZ.
    """

    method = method.lower()

    if method == "zip":
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
            if os.path.isdir(input_path):
                for root, dirs, files in os.walk(input_path):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, input_path)
                        z.write(full_path, rel_path)
            else:
                z.write(input_path, os.path.basename(input_path))

    elif method in ("tar", "tgz", "gz"):
        mode = "w:gz" if method != "tar" else "w"

        with tarfile.open(output_path, mode) as tar:
            tar.add(input_path, arcname=os.path.basename(input_path))

    else:
        raise ValueError(f"Método de compresión no soportado: {method}")

    return output_path


def auto_compress(path: str, method: str):
    """
    Atajo general para compresión automática.
    """
    base, _ = os.path.splitext(path)
    ext = {"zip": "zip", "tar": "tar", "gz": "tgz"}[method]
    out = f"{base}.{ext}"
    return compress_file(path, out, method)
