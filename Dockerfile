# Image Python légère et version Debian stable.
FROM python:3.12-slim-bookworm

# Dossier de travail de l'application.
WORKDIR /app

# Dépendances système nécessaires à mysqlclient.
RUN apt-get \
    -o Acquire::ForceIPv4=true \
    -o Acquire::Retries=5 \
    update \
    && apt-get \
    -o Acquire::ForceIPv4=true \
    -o Acquire::Retries=5 \
    install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Installe les dépendances Python.
COPY requirements.txt .
RUN pip install \
    --no-cache-dir \
    --timeout 120 \
    --retries 5 \
    -r requirements.txt

# Copie le projet Django dans le conteneur.
COPY . .

# Port utilisé par Django.
EXPOSE 8000

# Lance le serveur Django.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]