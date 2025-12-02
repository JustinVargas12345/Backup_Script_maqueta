# Dockerfile ejemplo para Backup_Script_maqueta
# Incluye Python y clientes básicos (Postgres/MySQL/Mongo) en una imagen ligera.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalar paquetes de sistema necesarios (ejemplo Debian/Ubuntu)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       wget \
       gnupg \
       lsb-release \
       libpq-dev \
       postgresql-client \
       default-mysql-client \
       mongodb-clients \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements si existe
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt || true

# Copiar código
COPY . /app

# Usar src como módulo
ENV PYTHONPATH=/app/src

ENTRYPOINT ["python", "-m", "cli.app"]
