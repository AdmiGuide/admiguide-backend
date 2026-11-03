# AdmiGuide — Backend

API métier d’**AdmiGuide**, une application d’orientation administrative au Sénégal. Ce service **Django REST Framework** gère les utilisateurs, les situations administratives, le référentiel et le suivi des démarches. Il fait le lien entre le [frontend Angular](https://github.com/AdmiGuide/admiguide-frontend), **MySQL** et le [microservice FastAPI](https://github.com/AdmiGuide/admiguide-ai).

AdmiGuide propose une **orientation indicative** : il ne réalise pas les démarches à la place des usagers.

## Fonctionnalités

- **Orientation** : analyse des situations, questions complémentaires, résultats et historique.
- **Référentiel** : démarches, pièces, étapes, services administratifs et sources.
- **Suivi** : validation des étapes et calcul de la progression.
- **Chatbot contextuel** : contrôle d’accès, préparation du contexte et communication avec FastAPI pour expliquer une orientation sans la modifier.
- **Saisie vocale** : réception des fichiers audio et transmission à FastAPI pour transcription.
- **Comptes** : inscription, authentification JWT, profil et réinitialisation du mot de passe.
- **Administration** : gestion des utilisateurs, sources et signalements.

**MVP :** neuf démarches réparties entre passeports sénégalais, pensions après décès d’un fonctionnaire et foncier (dont autorisation d’occupation). L’analyse retourne `ORIENTATION`, `PRECISIONS_REQUISES` ou `SOURCES_INSUFFISANTES`.

## Technologies et architecture

**Stack :** Python 3.12, Django 6.1, Django REST Framework, MySQL, Simple JWT, drf-spectacular, django-cors-headers, Requests et Docker. Les versions exactes figurent dans `requirements.txt`.

```text
Frontend Angular
       |
       | API REST
       v
Backend Django (ce dépôt)
       |              |
       v              v
     MySQL         FastAPI / Groq
                   - Orientation RAG
                   - Chatbot contextuel
                   - Transcription vocale
```

**Angular communique uniquement avec Django.** Django vérifie les autorisations, conserve les données métier et sollicite FastAPI pour les fonctions d’IA.

## Installation en local

### Prérequis

- **Python 3.12** et un serveur **MySQL** accessible.
- Le microservice `admiguide-ai` configuré et démarré sur le port **8001** pour tester les fonctions d’IA.
- Selon le système, les bibliothèques MySQL nécessaires à `mysqlclient`.

### 1. Cloner et installer

```bash
git clone https://github.com/AdmiGuide/admiguide-backend.git
cd admiguide-backend
python -m venv venv
```

**Windows PowerShell :**

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**Linux / macOS :**

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Configurer `.env` et MySQL

Créer la base MySQL `admiguide_db` et un utilisateur disposant des droits nécessaires. Copier `.env.example` en `.env`, puis renseigner les valeurs locales :

```dotenv
DJANGO_SECRET_KEY=remplacer-par-une-cle-secrete-longue
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=admiguide_db
DB_USER=utilisateur_mysql
DB_PASSWORD=mot_de_passe_mysql
DB_HOST=127.0.0.1
DB_PORT=3306

AI_SERVICE_URL=http://127.0.0.1:8001
FRONTEND_URL=http://localhost:4200
```

Adapter les identifiants et le port MySQL si nécessaire. **Ne jamais publier `.env` ni des secrets.**

**CORS :** les origines autorisées sont actuellement fixées dans `config/settings.py` (`localhost:4200` et `127.0.0.1:4200`) ; la variable `CORS_ALLOWED_ORIGINS` de `.env.example` n’est pas encore utilisée par ce réglage.

### 3. Initialiser le référentiel

```bash
python manage.py migrate
python manage.py seed_mvp_referentiel
python manage.py seed_autorisation_occupation
python manage.py createsuperuser
```

**Les deux commandes `seed` sont nécessaires** : elles installent respectivement huit démarches et la neuvième, relative à l’autorisation d’occupation.

### 4. Démarrer Django

Démarrer MySQL et FastAPI, puis lancer :

```bash
python manage.py runserver 8000
```

- **Swagger :** http://127.0.0.1:8000/api/docs/
- **OpenAPI :** http://127.0.0.1:8000/api/schema/
- **Admin Django :** http://127.0.0.1:8000/admin/

En développement, les liens de réinitialisation du mot de passe sont affichés dans le terminal Django, sans envoi réel d’e-mail.

## Principales routes API

| Méthode | Route | Fonction |
| --- | --- | --- |
| `POST` | `/api/auth/register/` | Inscription |
| `POST` | `/api/auth/login/` | Connexion |
| `POST` | `/api/orientations/situations/` | Soumettre une situation |
| `GET` | `/api/orientations/situations/{public_id}/resultat/` | Consulter le résultat |
| `POST` | `/api/orientations/situations/{public_id}/chat/` | Interroger le chatbot |
| `POST` | `/api/orientations/transcribe/` | Transcrire un audio |

Les routes des précisions, du suivi, de l’historique et de l’administration sont décrites dans **Swagger**.

Le chatbot accepte une question et la page (`PRECISIONS`, `RESULTAT`, `SUIVI`), ainsi que certains champs contextuels (`question_id`, `terme_juridique`, `historique`). **Django reconstitue le contexte depuis la base et vérifie les droits** avant d’appeler FastAPI. Les situations privées sont réservées à leur propriétaire ; le suivi exige une connexion.

## Organisation du projet

```text
admiguide-backend/
├── accounts/         # Comptes et JWT
├── orientations/     # Orientation, suivi, chatbot et transcription
│   └── services/     # Logique métier et échanges avec FastAPI
├── referentiel/      # Démarches, étapes, pièces et sources
├── signalements/     # Signalements et traitement admin
├── config/           # Paramètres et routes Django
├── manage.py
├── requirements.txt
├── .env.example
└── Dockerfile
```

## Tests

```bash
python manage.py check
python manage.py test
python manage.py test orientations.test_chat_access
```

Les **4 tests d’accès au chatbot** ont été validés. Les parcours complets nécessitent également MySQL, FastAPI et Angular.

## Docker

Le `Dockerfile` construit le backend Django (port **8000**) :

```bash
docker build -t admiguide-backend .
```

L’image utilise `runserver` pour le développement. Le déploiement multi-services doit également configurer MySQL, FastAPI, les variables d’environnement et l’initialisation du référentiel.

## Dépôts associés

- [AdmiGuide Frontend — Angular](https://github.com/AdmiGuide/admiguide-frontend)
- [AdmiGuide AI — FastAPI, RAG et chatbot](https://github.com/AdmiGuide/admiguide-ai)

**Développeuse :** Dado Watt.
