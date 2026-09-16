from django.db import transaction

from orientations.models import (
    OrientationAdministrative,
    QuestionComplementaire,
)
from referentiel.models import DemarcheAdministrative

from .ai_service import analyser_situation


MVP_DEMARCHE_CODES = {
    "REMPLACEMENT_PASSEPORT_PERDU",
    "RETOUR_EFFETS_PERSONNELS",
    "NAISSANCE_ETRANGER",
    "DECES_FONCTIONNAIRE",
}


class OrientationServiceError(Exception):
    """Erreur pendant le traitement d'une analyse IA."""


def _get_reponses(situation) -> list[dict]:
    """Prépare les réponses déjà données dans le format attendu par FastAPI."""
    reponses = []

    for question in situation.questions.all().order_by("ordre"):
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
    """Remplace les questions encore sans réponse par les nouvelles."""
    with transaction.atomic():
        situation.questions.filter(reponse__isnull=True).delete()

        dernier_ordre = (
            situation.questions
            .order_by("-ordre")
            .values_list("ordre", flat=True)
            .first()
            or 0
        )

        for index, question in enumerate(questions, start=1):
            texte = question.get("texte")
            type_question = question.get("type_question")

            if not texte or not type_question:
                raise OrientationServiceError(
                    "AdmiGuide AI a retourné une question invalide."
                )

            QuestionComplementaire.objects.create(
                situation=situation,
                texte=texte,
                type_question=type_question,
                options=question.get("options", []),
                ordre=dernier_ordre + index,
            )


def _enregistrer_orientation(situation, resultat: dict) -> None:
    """Enregistre l'orientation définitive retournée par AdmiGuide AI."""
    code = resultat.get("demarche_code")
    resume = resultat.get("resume")

    if not code or not resume:
        raise OrientationServiceError(
            "AdmiGuide AI a retourné une orientation incomplète."
        )

    try:
        demarche = DemarcheAdministrative.objects.get(code=code)
    except DemarcheAdministrative.DoesNotExist as exc:
        raise OrientationServiceError(
            f"La démarche {code} n'existe pas dans le référentiel."
        ) from exc

    orientation_existante = OrientationAdministrative.objects.filter(
        situation=situation
    ).first()

    # Une nouvelle démarche invalide l'ancien suivi des étapes.
    if (
        orientation_existante
        and orientation_existante.demarche_id != demarche.id
    ):
        orientation_existante.suivis_etapes.all().delete()

    OrientationAdministrative.objects.update_or_create(
        situation=situation,
        defaults={
            "demarche": demarche,
            "resume": resume,
            "avertissement": resultat.get("avertissement", ""),
        },
    )

    # Une orientation définitive rend inutiles les questions sans réponse.
    situation.questions.filter(reponse__isnull=True).delete()


def analyser_et_enregistrer(situation) -> dict:
    """Analyse une situation avec AdmiGuide AI et enregistre son résultat."""
    demarche_codes = list(
        DemarcheAdministrative.objects.filter(
            code__in=MVP_DEMARCHE_CODES
        ).values_list("code", flat=True)
    )

    codes_manquants = MVP_DEMARCHE_CODES.difference(demarche_codes)
    if codes_manquants:
        raise OrientationServiceError(
            "Le référentiel MVP est incomplet : "
            + ", ".join(sorted(codes_manquants))
        )

    resultat = analyser_situation(
        situation=situation.description_initiale,
        pays_application=situation.pays_application,
        demarche_codes=demarche_codes,
        reponses=_get_reponses(situation),
    )

    statut = resultat.get("statut")

    if statut == "PRECISIONS_REQUISES":
        _enregistrer_questions(
            situation,
            resultat.get("questions", []),
        )
        return resultat

    if statut == "ORIENTATION":
        _enregistrer_orientation(situation, resultat)
        return resultat

    if statut == "SOURCES_INSUFFISANTES":
        # Évite de laisser d'anciennes questions inutiles à l'écran.
        situation.questions.filter(reponse__isnull=True).delete()
        return resultat

    raise OrientationServiceError(
        "AdmiGuide AI a retourné un statut inconnu."
    )
