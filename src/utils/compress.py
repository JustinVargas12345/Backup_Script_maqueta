import os
import tarfile
import zipfile
import shutil


def compress_file(input_path, methods):
    if isinstance(methods, str):
        methods = [methods]  # convertir a lista si es un string
    compressed_files = []
    for method in methods:
        method = method.lower()
        if method == "zip":
            output_path = input_path + ".zip"
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(input_path, os.path.basename(input_path))
            compressed_files.append(output_path)
        elif method == "tar":
            output_path = input_path + ".tar"
            with tarfile.open(output_path, "w") as tar:
                tar.add(input_path, arcname=os.path.basename(input_path))
            compressed_files.append(output_path)
        elif method == "gz":
            output_path = input_path + ".tgz"
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(input_path, arcname=os.path.basename(input_path))
            compressed_files.append(output_path)
        else:
            raise ValueError(f"Método de compresión inválido: {method}")

    return compressed_files



def auto_compress(path: str, method: str):
    """
    Atajo general para compresión automática.
    """
    base, _ = os.path.splitext(path)
    ext = {"zip": "zip", "tar": "tar", "gz": "tgz"}[method]
    out = f"{base}.{ext}"
    return compress_file(path, out, method)


