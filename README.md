# AdmiGuide Backend

Backend principal de **AdmiGuide**, une application web intelligente d’orientation administrative destinée à accompagner les usagers dans l’identification et la compréhension de démarches administratives sénégalaises.

Ce service gère les utilisateurs, les situations administratives, le référentiel des démarches, les signalements, le suivi des étapes et la communication avec le microservice d’intelligence artificielle `admiguide-ai`.

## Fonctionnalités principales

- Inscription et authentification avec JWT
- Gestion du profil utilisateur
- Création et modification d’une situation administrative
- Gestion du pays de résidence utilisé pour l’orientation
- Gestion des questions et réponses complémentaires
- Communication avec le microservice FastAPI
- Enregistrement de l’orientation proposée
- Consultation du résultat d’une orientation
- Historique des situations pour les utilisateurs connectés
- Suivi de la progression des étapes d’une démarche
- Gestion des démarches, pièces requises, services et sources officielles
- Filtrage des sources affichées selon le pays concerné
- Création et traitement des signalements
- Administration des utilisateurs, des sources et des signalements

## Technologies utilisées

- Python
- Django 6
- Django REST Framework
- MySQL
- Simple JWT
- drf-spectacular
- django-cors-headers
- Requests
- python-dotenv

## Architecture

Le backend Django constitue l’API métier principale entre le frontend Angular, la base de données MySQL et le microservice IA.

```text
Frontend Angular
       |
       v
Django REST Framework
       |
       +------> MySQL
       |
       v
AdmiGuide AI
FastAPI + RAG + LLM
```

Le service IA peut retourner trois états :

- `ORIENTATION` : une démarche a été identifiée ;
- `PRECISIONS_REQUISES` : des informations complémentaires sont nécessaires ;
- `SOURCES_INSUFFISANTES` : les sources disponibles ne permettent pas de fournir une orientation fiable.

## Structure principale

```text
admiguide-backend/
|
|-- accounts/          # Authentification, profils et gestion des utilisateurs
|-- orientations/      # Situations, questions, réponses, orientations et suivi
|-- referentiel/       # Démarches, étapes, pièces, services et sources
|-- signalements/      # Signalements des usagers et traitement administratif
|-- config/            # Configuration Django
|-- manage.py
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/AdmiGuide/admiguide-backend.git
cd admiguide-backend
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
```

Sous Windows PowerShell :

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## Configuration

Créer un fichier `.env` à la racine du projet à partir de `.env.example`.

```env
# Django
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# MySQL
DB_NAME=admiguide_db
DB_USER=
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306

# Angular
CORS_ALLOWED_ORIGINS=http://localhost:4200

# FastAPI
AI_SERVICE_URL=http://127.0.0.1:8001
```

Adapter les paramètres MySQL selon la configuration locale.

## Base de données

Appliquer les migrations :

```bash
python manage.py migrate
```

Initialiser le référentiel utilisé par le MVP :

```bash
python manage.py seed_mvp_referentiel
```

## Lancement

Démarrer Django :

```bash
python manage.py runserver 8000
```

L’API est disponible sur :

```text
http://127.0.0.1:8000/
```

Le microservice `admiguide-ai` doit également être démarré sur :

```text
http://127.0.0.1:8001/
```

## Documentation API

Swagger est disponible sur :

```text
http://127.0.0.1:8000/api/docs/
```

Le schéma OpenAPI est disponible sur :

```text
http://127.0.0.1:8000/api/schema/
```

## Principaux endpoints

### Authentification

```text
POST  /api/auth/register/
POST  /api/auth/login/
POST  /api/auth/refresh/
POST  /api/auth/logout/
GET   /api/auth/profile/
PATCH /api/auth/profile/
```

### Orientation

```text
POST  /api/orientations/situations/
PATCH /api/orientations/situations/{public_id}/
GET   /api/orientations/situations/{public_id}/questions/
POST  /api/orientations/situations/{public_id}/reponses/
GET   /api/orientations/situations/{public_id}/resultat/
GET   /api/orientations/historique/
PATCH /api/orientations/situations/{public_id}/etapes/{etape_id}/
```

### Administration

```text
GET   /api/auth/admin/users/
GET   /api/auth/admin/users/{id}/
PATCH /api/auth/admin/users/{id}/

GET   /api/referentiel/admin/sources/
PATCH /api/referentiel/admin/sources/{id}/control/

GET   /api/signalements/admin/
GET   /api/signalements/admin/{id}/
PATCH /api/signalements/admin/{id}/
```

### Signalements

```text
POST /api/signalements/situations/{public_id}/
```

## Scénarios couverts par le MVP

AdmiGuide prend actuellement en charge quatre situations :

- remplacement d’un passeport sénégalais perdu ;
- retour définitif au Sénégal avec des effets personnels ;
- transcription d’une naissance survenue à l’étranger ;
- réversion de pension et capital-décès d’un fonctionnaire décédé en activité.

## Gestion des sources

Les sources officielles sont associées aux démarches administratives et disposent d’un statut :

```text
DISPONIBLE
INDISPONIBLE
A_VERIFIER
```

Lorsque plusieurs sources existent pour une même démarche, AdmiGuide filtre les sources affichées afin de ne présenter que celles correspondant au contexte géographique de la situation lorsque cette information est disponible.

## Projet associé

L’analyse intelligente des situations est assurée par :

```text
admiguide-ai
```

Ce microservice FastAPI utilise une architecture RAG à partir de sources administratives officielles.

## Développeuse

**Dado Watt**