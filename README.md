# AdmiGuide Backend

API métier d’**AdmiGuide**, une application d’orientation administrative qui aide les usagers à identifier les démarches sénégalaises adaptées à leur situation, à comprendre les étapes proposées et à suivre leur progression.

Ce dépôt contient le backend **Django REST Framework** : gestion des comptes, situations administratives, questions complémentaires, référentiel officiel, résultats d’orientation, suivi et signalements. Il sert d’intermédiaire entre le frontend Angular et le microservice `admiguide-ai` (FastAPI, RAG et modèle de langage).

> **Périmètre du MVP :** les parcours documentés dans ce dépôt sont principalement ceux des passeports sénégalais, des pensions après décès d’un fonctionnaire et du foncier, avec un référentiel centré sur les cas étudiés à Dakar. AdmiGuide fournit une **orientation indicative**, pas une décision administrative, et n’effectue pas les démarches à la place de l’usager.

## Fonctionnalités

### Orientation et espace usager

- Saisie d’une situation en langage naturel, accessible même sans compte (description de 20 à 1 500 caractères validée par le service IA ; longueur maximale également définie dans le modèle Django).
- Analyse par `admiguide-ai`, avec trois issues : `ORIENTATION`, `PRECISIONS_REQUISES` ou `SOURCES_INSUFFISANTES`.
- Questions complémentaires, validation des réponses et nouvelle analyse tenant compte des informations déjà fournies.
- Résultat associé à un identifiant public UUID : démarche, résumé, éventuel avertissement, étapes, pièces, services, coûts et délais indicatifs et sources officielles disponibles.
- Possibilité de modifier la description d’une situation et de relancer l’analyse.
- Historique des situations des utilisateurs connectés.
- Suivi des étapes : cocher ou décocher une étape et mettre à jour le pourcentage d’avancement.
- Signalement d’informations incorrectes, incomplètes, obsolètes ou d’un autre problème sur une orientation.
- **Saisie vocale :** réception d’un fichier audio depuis Angular, transmission au microservice IA pour transcription, puis retour du texte à l’interface.

### Comptes et administration

- Inscription et connexion par adresse e-mail, avec authentification **JWT** (Simple JWT).
- Consultation et modification du profil ; déconnexion par invalidation du refresh token.
- Demande et confirmation de réinitialisation du mot de passe par lien envoyé à l’adresse e-mail.
- Administration des utilisateurs : liste, recherche, filtres et activation/désactivation.
- Administration des sources : liste, recherche, filtres par statut et type, contrôle manuel du statut.
- Administration des signalements : consultation, recherche, filtres et changement de statut.
- Pagination des listes d’administration (5 éléments par défaut, ajustable jusqu’à 20).

## Technologies

- **Python 3.12** dans le Dockerfile fourni ;
- **Django 6.1.1** et **Django REST Framework 3.18.1** ;
- **MySQL**, via `mysqlclient` ;
- **Simple JWT** pour l’authentification et la gestion des refresh tokens ;
- **drf-spectacular** pour OpenAPI et Swagger ;
- **django-cors-headers** ;
- **Requests** pour les appels à FastAPI ;
- **python-dotenv** pour la configuration locale ;
- **Docker** pour la conteneurisation.

Les versions effectivement figées sont consultables dans `requirements.txt`.

## Architecture

```text
Navigateur / Angular (admiguide-frontend)
                |
                | API REST / JSON ; audio en multipart/form-data
                v
        Django REST Framework
          /            \
         v              v
       MySQL       AdmiGuide AI (FastAPI)
                         |
                         +-- Préparation de la demande avec Groq
                         +-- Recherche RAG dans ChromaDB
                         +-- Orientation via Groq
                         +-- Transcription via Whisper / FFmpeg
```

Angular n’appelle pas directement FastAPI. Django orchestre les échanges, conserve les situations et rattache les résultats de l’IA aux démarches et documents du référentiel local.

Pour une analyse, Django transmet à FastAPI la **situation**, la liste des **codes de démarches autorisés** et les **réponses complémentaires** déjà enregistrées. Les champs `pays_residence` et `pays_application` ne font plus partie de ce contrat d’entrée. Les éventuels avertissements sont conservés avec l’orientation.

### Structure du dépôt

```text
admiguide-backend/
├── accounts/                        # Comptes, JWT et réinitialisation du mot de passe
├── orientations/                    # Situations, réponses, résultats, suivi et proxy vocal
│   └── services/
│       ├── ai_service.py            # Appels HTTP au microservice FastAPI
│       └── orientation_service.py   # Orchestration et enregistrement des résultats
├── referentiel/                     # Démarches, pièces, étapes, services et sources
│   └── management/commands/
│       ├── seed_mvp_referentiel.py
│       └── seed_autorisation_occupation.py
├── signalements/                    # Signalements des usagers et traitement admin
├── config/                          # Paramètres, routes et pagination Django
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Démarches du MVP

Le backend reconnaît actuellement **neuf codes**, définis dans `orientations/services/orientation_service.py` et initialisés par les commandes du référentiel :

| Domaine | Code technique | Situation concernée |
| --- | --- | --- |
| Passeport | `DEMANDE_PASSEPORT_ORDINAIRE` | Première demande de passeport sénégalais |
| Passeport | `RENOUVELLEMENT_PASSEPORT` | Renouvellement d’un passeport existant |
| Passeport | `PASSEPORT_PERDU_OU_VOLE` | Perte ou vol d’un passeport |
| Pensions | `REVERSION_PENSION_CAPITAL_DECES_ACTIVITE` | Décès d’un fonctionnaire en activité |
| Pensions | `REVERSION_PENSION_APRES_RETRAITE` | Décès d’un fonctionnaire après son départ à la retraite |
| Foncier | `REGULARISATION_BAIL` | Régularisation par voie de bail |
| Foncier | `ACQUISITION_MUTATION_TITRE_FONCIER` | Acquisition ou mutation d’un bien disposant d’un titre foncier |
| Foncier | `TRANSFORMATION_BAIL_EN_TITRE_FONCIER` | Transformation d’un bail en titre foncier |
| Foncier | `TRANSFORMATION_AUTORISATION_OCCUPATION_EN_TITRE_FONCIER` | Examen d’une transformation à partir d’une autorisation d’occupation |

Les démarches foncières requièrent des vérifications administratives propres à chaque situation, notamment auprès des services des Domaines. Le résultat n’établit pas automatiquement un droit de propriété ou une éligibilité.

**Important :** `seed_mvp_referentiel` initialise les huit premières démarches ; la neuvième est ajoutée séparément par `seed_autorisation_occupation`. Il faut exécuter **les deux commandes**, en particulier après la création d’une nouvelle base de données, faute de quoi l’analyse signalera un référentiel incomplet.

## Installation locale

### 1. Cloner le dépôt

```bash
git clone https://github.com/AdmiGuide/admiguide-backend.git
cd admiguide-backend
```

### 2. Créer et activer un environnement virtuel

```bash
python -m venv venv
```

Sous Windows PowerShell :

```powershell
.\venv\Scripts\Activate.ps1
```

Sous Linux / macOS :

```bash
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

L’installation de `mysqlclient` peut nécessiter les bibliothèques de développement MySQL et les outils de compilation correspondants selon le système d’exploitation. Le conteneur Docker inclut les dépendances système utilisées lors de sa compilation.

### 4. Préparer MySQL et le fichier `.env`

Créer une base MySQL et un utilisateur disposant des droits nécessaires, puis copier `.env.example` en `.env` à la racine du dépôt.

Exemple de configuration locale :

```dotenv
DJANGO_SECRET_KEY=remplacer-par-une-cle-secrete-longue
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=admiguide_db
DB_USER=mon_utilisateur_mysql
DB_PASSWORD=mon_mot_de_passe_mysql
DB_HOST=127.0.0.1
DB_PORT=3306

CORS_ALLOWED_ORIGINS=http://localhost:4200
FRONTEND_URL=http://localhost:4200
AI_SERVICE_URL=http://127.0.0.1:8001
```

Ne jamais committer `.env` ou des clés secrètes. `DJANGO_SECRET_KEY` est obligatoire au démarrage.

**Remarque sur CORS :** la branche actuelle déclare `CORS_ALLOWED_ORIGINS` dans `.env.example`, mais `config/settings.py` fixe encore les origines autorisées à `http://localhost:4200` et `http://127.0.0.1:4200`. La variable d’environnement n’est donc pas encore utilisée pour ce réglage ; il faudra adapter les paramètres avant un déploiement sur une autre origine.

### 5. Créer les tables et initialiser le référentiel

Depuis la racine du dépôt :

```bash
python manage.py migrate
python manage.py seed_mvp_referentiel
python manage.py seed_autorisation_occupation
```

Les commandes d’initialisation synchronisent les démarches et leurs éléments associés. Celle de l’autorisation d’occupation peut être relancée pour mettre à jour cette démarche sans en créer une seconde.

Pour créer un compte administrateur Django :

```bash
python manage.py createsuperuser
```

### 6. Démarrer les services

Démarrer MySQL et **`admiguide-ai`** (par défaut sur `http://127.0.0.1:8001`) avant de tester une orientation ou une transcription. Puis lancer Django :

```bash
python manage.py runserver 8000
```

API : `http://127.0.0.1:8000/api/`

Documentation :

- Swagger : `http://127.0.0.1:8000/api/docs/`
- Schéma OpenAPI : `http://127.0.0.1:8000/api/schema/`
- Administration Django : `http://127.0.0.1:8000/admin/`

## Principaux endpoints

Les URL ci-dessous sont définies dans les fichiers `urls.py` des applications. Les routes d’administration et d’historique sont protégées par les permissions Django REST Framework.

### Authentification et comptes

```text
POST  /api/auth/register/
POST  /api/auth/login/
POST  /api/auth/refresh/
POST  /api/auth/logout/
GET   /api/auth/profile/
PATCH /api/auth/profile/
POST  /api/auth/password-reset/
POST  /api/auth/password-reset-confirm/{uidb64}/{token}/

GET   /api/auth/admin/users/
GET   /api/auth/admin/users/{id}/
PATCH /api/auth/admin/users/{id}/
```

L’authentification des routes protégées utilise l’en-tête `Authorization: Bearer <access_token>`. Les access tokens durent **15 minutes**, les refresh tokens **7 jours** ; leur rotation et leur mise en liste noire sont activées dans `config/settings.py`.

**Réinitialisation du mot de passe :** en développement, `EMAIL_BACKEND` utilise le backend console Django ; le lien de réinitialisation est **affiché dans le terminal**, et non envoyé à une véritable boîte e-mail. Un fournisseur d’envoi doit être configuré pour la production.

### Situations, orientation et suivi

```text
POST  /api/orientations/situations/
PATCH /api/orientations/situations/{public_id}/
GET   /api/orientations/situations/{public_id}/questions/
POST  /api/orientations/situations/{public_id}/reponses/
GET   /api/orientations/situations/{public_id}/resultat/
GET   /api/orientations/historique/
PATCH /api/orientations/situations/{public_id}/etapes/{etape_id}/
POST  /api/orientations/transcribe/
```

- **Création et précisions :** accessibles aux visiteurs sans compte ; si l’utilisateur est connecté, la situation lui est rattachée.
- **Accès aux situations :** une situation anonyme est accessible avec son UUID public ; une situation liée à un compte est réservée à son propriétaire.
- **Historique et progression :** réservés aux utilisateurs authentifiés. La modification d’une étape exige en outre que la situation appartienne au compte connecté.
- **Transcription :** requête `multipart/form-data` avec un fichier dans le champ `audio` ; taille maximale contrôlée à **10 Mio**. Django transmet l’audio à `/transcribe` sur le service IA et retourne sa transcription.

Exemple de création d’une situation :

```http
POST /api/orientations/situations/
Content-Type: application/json
```

```json
{
  "description_initiale": "J'ai perdu mon passeport sénégalais à Dakar et je souhaite le remplacer."
}
```

La réponse contient notamment `public_id`, `description_initiale`, `date_creation` et `analyse`. En fonction des informations disponibles, l’objet `analyse` porte le statut `ORIENTATION`, `PRECISIONS_REQUISES` ou `SOURCES_INSUFFISANTES`.

Lorsque des précisions sont demandées, les questions sont récupérées sur l’endpoint `/questions/`, puis les réponses sont envoyées sous la forme :

```json
{
  "reponses": [
    {
      "question_id": 1,
      "contenu": "Oui"
    }
  ]
}
```

`question_id` doit correspondre à une question réellement renvoyée pour cette situation : la valeur `1` n’est ici qu’un exemple de format.

Exemple de mise à jour d’une étape :

```json
{
  "terminee": true
}
```

La réponse fournit l’identifiant de l’étape, son état et la progression (`terminees`, `total`, `pourcentage`).

### Sources et signalements

```text
GET   /api/referentiel/admin/sources/
PATCH /api/referentiel/admin/sources/{id}/control/

POST  /api/signalements/situations/{public_id}/
GET   /api/signalements/admin/
GET   /api/signalements/admin/{id}/
PATCH /api/signalements/admin/{id}/
```

Les sources sont liées aux démarches du référentiel. Leurs statuts sont :

```text
DISPONIBLE
INDISPONIBLE
A_VERIFIER
```

**Seules les sources au statut `DISPONIBLE`** sont retournées dans la liste `sources` d’un résultat d’orientation. Le code actuel ne filtre pas cette liste par pays de résidence : ce champ a été retiré du modèle concerné.

Les types de source permettent de distinguer les pages web, documents et autres supports du référentiel. Les vues administrateur appliquent des filtres, la recherche et la pagination selon l’endpoint.

Les signalements d’usagers nécessitent une connexion ; leur traitement administratif utilise les statuts `NOUVEAU`, `EN_COURS` et `TRAITE`.

## Tests et vérifications

Pour exécuter les tests Django du dépôt :

```bash
python manage.py test
```

Pour vérifier la configuration Django :

```bash
python manage.py check
```

Ces commandes vérifient le projet Django, mais **ne remplacent pas** les tests d’intégration réels avec MySQL, le service `admiguide-ai` et le frontend Angular.

## Docker

Le dépôt contient un `Dockerfile` basé sur `python:3.12-slim-bookworm`. Il installe les bibliothèques nécessaires à `mysqlclient`, les dépendances Python, puis expose le port **8000**.

Le `CMD` actuel démarre :

```bash
python manage.py runserver 0.0.0.0:8000
```

Ce lancement est adapté aux essais de conteneurisation **en développement**, mais **ne constitue pas une configuration de production**. La configuration définitive du réseau, des volumes, des variables d’environnement, du démarrage MySQL et du serveur applicatif sera vérifiée avec le dépôt de déploiement avant la fusion dans `develop` puis `main`.

Pour un simple build de l’image du backend depuis ce dossier :

```bash
docker build -t admiguide-backend .
```

La construction de l’image ne crée pas la base MySQL, n’exécute pas automatiquement `migrate` et n’initialise pas le référentiel. Ces étapes restent nécessaires lors du premier démarrage dans un nouvel environnement.

## Dépôts associés

- [`admiguide-frontend`](https://github.com/AdmiGuide/admiguide-frontend) : application Angular et interface utilisateur.
- [`admiguide-ai`](https://github.com/AdmiGuide/admiguide-ai) : analyse par modèle de langage, recherche RAG et transcription audio.

## Développement

Projet AdmiGuide — **Dado Watt**.
