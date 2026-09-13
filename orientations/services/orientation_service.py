# Permet d'enregistrer plusieurs changements ensemble.
from django.db import transaction

# Modèles utilisés pour enregistrer le résultat de l'analyse.
from orientations.models import (
    OrientationAdministrative,
    QuestionComplementaire,
)

# Référentiel des démarches connues par Django.
from referentiel.models import DemarcheAdministrative

# Service chargé de communiquer avec AdmiGuide AI.
from .ai_service import analyser_situation


class OrientationServiceError(Exception):
    """Erreur pendant le traitement d'une analyse IA."""


def _get_reponses(situation) -> list[dict]:
    """Prépare les réponses déjà données dans le format attendu par FastAPI."""

    reponses = []

    for question in situation.questions.all().order_by("ordre"):
        # Ignore les questions auxquelles l'utilisateur n'a pas encore répondu.
        if not hasattr(question, "reponse"):
            continue

        reponses.append(
            {
                "texte_question": question.texte,
                "contenu": question.reponse.contenu,
            }
        )

    return reponses


def _enregistrer_questions(situation, questions: list[dict]) -> None:
    """Enregistre les nouvelles questions demandées par AdmiGuide AI."""

    with transaction.atomic():
        # Supprime uniquement les anciennes questions restées sans réponse.
        situation.questions.filter(
            reponse__isnull=True
        ).delete()

        # Continue l'ordre après les questions déjà répondues.
        dernier_ordre = (
            situation.questions
            .order_by("-ordre")
            .values_list("ordre", flat=True)
            .first()
            or 0
        )

        for index, question in enumerate(questions, start=1):
            QuestionComplementaire.objects.create(
                situation=situation,
                texte=question["texte"],
                type_question=question["type_question"],
                options=question.get("options", []),
                ordre=dernier_ordre + index,
            )


def _enregistrer_orientation(situation, resultat: dict) -> None:
    """Enregistre l'orientation définitive retournée par AdmiGuide AI."""

    code = resultat["demarche_code"]

    try:
        demarche = DemarcheAdministrative.objects.get(code=code)

    except DemarcheAdministrative.DoesNotExist as exc:
        raise OrientationServiceError(
            f"La démarche {code} n'existe pas dans le référentiel."
        ) from exc

    # Crée ou met à jour l'orientation de cette situation.
    OrientationAdministrative.objects.update_or_create(
        situation=situation,
        defaults={
            "demarche": demarche,
            "resume": resultat["resume"],
            "avertissement": resultat.get("avertissement", ""),
        },
    )


def analyser_et_enregistrer(situation) -> dict:
    """
    Analyse une situation avec AdmiGuide AI
    puis enregistre le résultat utile dans Django.
    """

    # Django transmet à l'IA toutes les démarches autorisées.
    demarche_codes = list(
        DemarcheAdministrative.objects.values_list(
            "code",
            flat=True,
        )
    )

    if not demarche_codes:
        raise OrientationServiceError(
            "Aucune démarche n'est disponible dans le référentiel."
        )

    # Récupère les éventuelles réponses déjà données.
    reponses = _get_reponses(situation)

    # Appelle le microservice AdmiGuide AI.
    resultat = analyser_situation(
        situation=situation.description_initiale,
        pays_application=situation.pays_application,
        demarche_codes=demarche_codes,
        reponses=reponses,
    )

    statut = resultat.get("statut")

    # L'IA a besoin d'informations supplémentaires.
    if statut == "PRECISIONS_REQUISES":
        _enregistrer_questions(
            situation,
            resultat.get("questions", []),
        )
        return resultat

    # L'IA a identifié la démarche.
    if statut == "ORIENTATION":
        _enregistrer_orientation(
            situation,
            resultat,
        )
        return resultat

    # Les sources ne permettent pas une réponse fiable.
    if statut == "SOURCES_INSUFFISANTES":
        return resultat

    # Sécurité si FastAPI retourne un statut inattendu.
    raise OrientationServiceError(
        "AdmiGuide AI a retourné un statut inconnu."
    )