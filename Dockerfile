FROM python:3.11-slim

# Metadata
LABEL maintainer="Backup_Script_maqueta"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

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
# To include MongoDB: docker build --build-arg INSTALL_MONGO=true -t backup_script:local .
# To include SQL Server tools: docker build --build-arg INSTALL_MSSQL=true -t backup_script:local .
ARG INSTALL_MONGO=false
ARG INSTALL_MSSQL=false

RUN if [ "${INSTALL_MONGO}" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends mongodb-clients || true; \
      rm -rf /var/lib/apt/lists/*; \
    fi

RUN if [ "${INSTALL_MSSQL}" = "true" ]; then \
      echo "Note: mssql-tools installation requires Microsoft repository setup. See README for details."; \
    fi

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project source
COPY . /app

# Make sure src is on PYTHONPATH so CLI can be run as `python src/cli.py`
ENV PYTHONPATH=/app/src

# Default entrypoint: run the CLI
ENTRYPOINT ["python", "src/cli.py"]

# Default CMD shows help. Users should override CMD to run specific commands.
CMD ["--help"]
