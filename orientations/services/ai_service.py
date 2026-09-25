import requests
from django.conf import settings


class AIServiceError(Exception):
    """Erreur lors de la communication avec AdmiGuide AI."""


def analyser_situation(
    situation: str,
    demarche_codes: list[str],
    pays_application: str | None = None,
    pays_residence: str | None = None,
    reponses: list[dict] | None = None,
) -> dict:
    """
    Envoie une situation à AdmiGuide AI
    et retourne sa réponse JSON.
    """

    # Données attendues par l'endpoint FastAPI /analyze.
    payload = {
        "situation": situation,
        "pays_application": pays_application,
        "pays_residence": pays_residence,
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