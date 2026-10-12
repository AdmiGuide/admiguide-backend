import requests
from django.conf import settings


class AIServiceError(Exception):
    """Erreur lors de la communication avec AdmiGuide AI."""


def analyser_situation(
    situation: str,
    demarche_codes: list[str],
    reponses: list[dict] | None = None,
) -> dict:
    """
    Envoie une situation à AdmiGuide AI
    et retourne sa réponse JSON.
    """

    # Données attendues par l'endpoint FastAPI /analyze.
    payload = {
        "situation": situation,
        "demarche_codes": demarche_codes,
        "reponses": reponses or [],
    }

    try:
        # Appelle le microservice IA.
        response = requests.post(
            f"{settings.AI_SERVICE_URL}/analyze",
            json=payload,
            timeout=75,
        )

        # Déclenche une erreur si FastAPI renvoie 4xx ou 5xx.
        response.raise_for_status()

    except requests.RequestException as exc:
        raise AIServiceError(
            "Le service AdmiGuide AI est indisponible."
        ) from exc

    try:
        # Retourne la réponse produite par FastAPI.
        return response.json()

    except ValueError as exc:
        raise AIServiceError(
            "AdmiGuide AI a retourné une réponse invalide."
        ) from exc


    
def transcrire_audio(audio_file) -> dict:
    """
    Transmet un enregistrement vocal à AdmiGuide AI
    et retourne la transcription produite par le microservice.
    """

    # Prépare le fichier pour un envoi en multipart/form-data.
    #
    # - audio_file.name : nom original du fichier ;
    # - audio_file.file : contenu binaire réel du fichier reçu par Django ;
    # - content_type    : type MIME, par exemple audio/webm ou audio/mpeg.
    files = {
        "audio": (
            audio_file.name,
            audio_file.file,
            audio_file.content_type
            or "application/octet-stream",
        )
    }

    try:
        # Transmet directement l'enregistrement au microservice FastAPI.
        #
        # Django ne nettoie ni ne transcrit l'audio :
        # ces traitements restent la responsabilité d'AdmiGuide AI.
        response = requests.post(
            f"{settings.AI_SERVICE_URL}/transcribe",
            files=files,

            # Évite qu'une transcription trop longue
            # bloque indéfiniment la requête Django.
            timeout=75,
        )

        # Déclenche une exception si FastAPI retourne
        # une erreur HTTP comme 400, 500 ou 503.
        response.raise_for_status()

    except requests.RequestException as exc:
        raise AIServiceError(
            "Le service de transcription est indisponible."
        ) from exc

    try:
        # Convertit la réponse JSON de FastAPI
        # en dictionnaire Python.
        data = response.json()

    except ValueError as exc:
        raise AIServiceError(
            "Le service de transcription a retourné une réponse invalide."
        ) from exc

    transcription = data.get("transcription")

    # Vérifie que la transcription existe réellement
    # et qu'elle contient du texte exploitable.
    if (
        not isinstance(transcription, str)
        or not transcription.strip()
    ):
        raise AIServiceError(
            "Aucune transcription valide n'a été retournée."
        )

    return data