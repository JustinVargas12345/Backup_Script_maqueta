import os
import tarfile
import zipfile
import shutil


def compress_file(input_path, methods):
    """
    Comprime archivo o carpeta usando uno o varios métodos.
    Devuelve lista con rutas generadas.
    """
    if isinstance(methods, str):
        methods = [methods]

    compressed_files = []

    for method in methods:
        method = method.lower()

        # ZIP
        if method == "zip":
            output_path = input_path + ".zip"
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.isdir(input_path):
                    # ZIP para carpetas
                    for root, dirs, files in os.walk(input_path):
                        for file in files:
                            full = os.path.join(root, file)
                            arc = os.path.relpath(full, input_path)
                            z.write(full, arcname=arc)
                else:
                    z.write(input_path, os.path.basename(input_path))

            compressed_files.append(output_path)

        # TAR
        elif method == "tar":
            output_path = input_path + ".tar"
            with tarfile.open(output_path, "w") as tar:
                tar.add(input_path, arcname=os.path.basename(input_path))
            compressed_files.append(output_path)

        # TAR.GZ
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
    Envuelve compress_file() para un solo método.
    Mantiene el nombre original y devuelve la ruta generada.
    """
    method = method.lower()
    result = compress_file(path, method)
    return result[0]  # devuelve el archivo generado
