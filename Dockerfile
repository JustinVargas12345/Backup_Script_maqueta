FROM python:3.11-slim

# Metadata
LABEL maintainer="Justin <you@example.com>"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install core OS packages and common DB clients available in Debian repos.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       wget \
       gnupg \
       lsb-release \
       build-essential \
       default-mysql-client \
       postgresql-client \
       unzip \
       zip \
       tar \
       gzip \
    && rm -rf /var/lib/apt/lists/*

# Optional: install MongoDB tools or SQL Server tools during build via build-args.
# These are disabled by default because they increase image size and may require
# adding external APT repositories (for mssql-tools) or different package names
# depending on distribution. See README for instructions.
ARG INSTALL_MONGO=false
ARG INSTALL_MSSQL=false

RUN if [ "${INSTALL_MONGO}" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends mongodb-clients || true; \
      rm -rf /var/lib/apt/lists/*; \
    fi

RUN if [ "${INSTALL_MSSQL}" = "true" ]; then \
      echo "mssql-tools installation requested. Follow README instructions to enable this step manually."; \
    fi

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project source
COPY . /app

# Make sure src is on PYTHONPATH so CLI can be run as `python src/cli.py`
ENV PYTHONPATH=/app/src

# Default entrypoint: show help. Users should override CMD to run specific commands.
ENTRYPOINT ["python", "src/cli.py"]

# Example default CMD (no args will print help). Override when running container.
CMD ["--help"]
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
