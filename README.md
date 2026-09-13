# AdmiGuide Backend

Backend principal de **AdmiGuide**, une application web intelligente d'orientation administrative destinée à accompagner les usagers dans l'identification et la compréhension des démarches administratives sénégalaises.

Ce projet assure la gestion des utilisateurs, des situations administratives, du référentiel des démarches et la communication avec le microservice d'intelligence artificielle `admiguide-ai`.

## Fonctionnalités principales

- Inscription et authentification des utilisateurs avec JWT
- Gestion du profil utilisateur
- Création et modification d'une situation administrative
- Gestion des questions et réponses complémentaires
- Communication avec le service IA AdmiGuide
- Enregistrement des orientations proposées
- Consultation du résultat d'une orientation
- Gestion de l'historique des situations
- Gestion du référentiel des démarches administratives
- Gestion des pièces requises, services compétents et sources officielles

## Technologies utilisées

- Python
- Django
- Django REST Framework
- MySQL
- Simple JWT
- drf-spectacular
- Requests
- python-dotenv

## Architecture

Le backend Django joue le rôle d'API métier principale entre le frontend Angular, la base de données MySQL et le microservice IA.

```text
Frontend Angular
       |
       v
Django REST Framework
       |
       +------> MySQL
       |
       v
AdmiGuide AI - FastAPI
       |
       v
RAG + LLM
```

Le service IA peut retourner trois types de résultats :

- `ORIENTATION` : une démarche administrative a été identifiée ;
- `PRECISIONS_REQUISES` : des informations complémentaires sont nécessaires ;
- `SOURCES_INSUFFISANTES` : les sources disponibles ne permettent pas de fournir une orientation fiable.

## Structure principale

```text
admiguide-backend/
|
|-- accounts/          # Authentification et profils utilisateurs
|-- orientations/      # Situations, questions, réponses et orientations
|-- referentiel/       # Démarches, pièces, services et sources
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

Adapter les informations MySQL selon la configuration locale.

## Base de données

Créer la base de données MySQL puis appliquer les migrations :

```bash
python manage.py migrate
```

Initialiser les données du référentiel nécessaires au MVP :

```bash
python manage.py seed_mvp_referentiel
```

## Lancement du serveur

```bash
python manage.py runserver 8000
```

L'API Django est alors disponible à l'adresse :

```text
http://127.0.0.1:8000/
```

Le microservice `admiguide-ai` doit également être démarré sur :

```text
http://127.0.0.1:8001/
```

## Principaux endpoints

### Authentification

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/profile/
PATCH /api/auth/profile/
```

### Orientation administrative

```text
POST  /api/orientations/situations/
PATCH /api/orientations/situations/{public_id}/
GET   /api/orientations/situations/{public_id}/questions/
POST  /api/orientations/situations/{public_id}/reponses/
GET   /api/orientations/situations/{public_id}/resultat/
GET   /api/orientations/historique/
```

## Scénarios couverts par le MVP

Le référentiel actuel prend en charge les situations suivantes :

- remplacement d'un passeport sénégalais perdu ;
- retour définitif au Sénégal avec des effets personnels ;
- transcription d'une naissance survenue à l'étranger ;
- réversion de pension et capital-décès d'un fonctionnaire décédé en activité.

## Projet associé

Le traitement intelligent des situations administratives est assuré par le microservice :

```text
admiguide-ai
```

Il utilise FastAPI ainsi qu'une architecture RAG pour analyser les situations à partir de sources administratives officielles.

## Développeuse

**Dado Watt**