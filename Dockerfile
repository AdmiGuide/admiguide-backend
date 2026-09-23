# Image Python légère.
FROM python:3.12-slim

# Dossier de travail de l'application.
WORKDIR /app

# Dépendances système nécessaires à mysqlclient.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Installe les dépendances Python.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le projet Django dans le conteneur.
COPY . .

# Port utilisé par Django.
EXPOSE 8000

# Lance le serveur Django.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]