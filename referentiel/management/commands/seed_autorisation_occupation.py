"""
Ajoute au référentiel AdmiGuide le parcours pour les personnes
ayant une autorisation d'occuper un terrain domanial à usage d'habitation.

Commande : python manage.py seed_autorisation_occupation

Cette commande est indépendante du seed MVP historique : elle n'efface
aucune démarche et peut être relancée sans créer de doublons.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from referentiel.models import (
    Administration,
    DemarcheAdministrative,
    EtapeDemarche,
    PieceRequise,
    ServiceAdministratif,
    SourceAdministrative,
    TypeSource,
)


CODE_DEMARCHE = "TRANSFORMATION_AUTORISATION_OCCUPATION_EN_TITRE_FONCIER"
URL_FICHE_OFFICIELLE = (
    "https://finances.gouv.sn/services-demarches/"
    "transformation-dun-bail-en-titre-foncier-SXYgqIuY_L1kggG6fLZQi"
)
URL_LOI = "https://www.dri.gouv.sn/loi-n%C2%B0-201731-du-15-juillet-2017"


class Command(BaseCommand):
    """Crée ou actualise le parcours « autorisation d'occupation »."""

    help = "Ajoute la transformation d'une autorisation d'occuper en titre foncier."

    @transaction.atomic
    def handle(self, *args, **options):
        # Réutilise le service administratif déjà configuré pour le foncier.
        dgid, _ = Administration.objects.get_or_create(
            nom="Direction générale des Impôts et des Domaines",
            defaults={"sigle": "DGID"},
        )
        service, _ = ServiceAdministratif.objects.get_or_create(
            administration=dgid,
            nom="Bureau des Domaines territorialement compétent",
            defaults={"adresse": "", "contact": ""},
        )

        # Le code métier est différent du code de transformation d'un bail.
        demarche, _ = DemarcheAdministrative.objects.update_or_create(
            code=CODE_DEMARCHE,
            defaults={
                "intitule": (
                    "Devenir propriétaire d'un terrain avec une "
                    "autorisation d'occupation"
                ),
                "description": (
                    "Permet au bénéficiaire d'une autorisation "
                    "d'occuper un terrain domanial à usage d'habitation "
                    "de demander son inscription en pleine propriété, "
                    "sous réserve de la vérification du titre et des "
                    "conditions prévues par les textes applicables."
                ),
                "cout_indicatif": (
                    "À confirmer ; cession gratuite possible sous conditions"
                ),
                "delai_indicatif": (
                    "À confirmer auprès de l'administration"
                ),
            },
        )
        demarche.services.set([service])

        # Trois étapes compréhensibles, sans garantir l'acceptation du dossier.
        etapes = [
            (
                "Préparer une demande écrite et les documents prouvant "
                "votre droit d'occuper le terrain."
            ),
            (
                "Déposer votre dossier auprès du service compétent "
                "de l'Enregistrement et des Domaines."
            ),
            (
                "Faire examiner le dossier par l'administration. "
                "Si la demande est acceptée, le transfert de propriété "
                "et l'établissement du titre foncier pourront être réalisés."
            ),
        ]
        for ordre, description in enumerate(etapes, start=1):
            EtapeDemarche.objects.update_or_create(
                demarche=demarche,
                ordre=ordre,
                defaults={"description": description},
            )
        demarche.etapes.exclude(ordre__in=range(1, len(etapes) + 1)).delete()

        # Pièces décrites dans la fiche du ministère des Finances.
        # La quittance est indiquée par la fiche ; sa pertinence doit
        # être confirmée en fonction des redevances effectivement dues.
        pieces = [
            ("Demande écrite au Directeur de l'Enregistrement, des Domaines et du Timbre", True),
            ("Copie certifiée conforme de l'autorisation d'occuper", True),
            ("Copie certifiée conforme de la carte nationale d'identité (personne physique)", True),
            ("Justificatif du statut de la société (personne morale)", False),
            ("Quittance de paiement des redevances d'occupation, si applicable", False),
        ]
        # La synchronisation évite les doublons lorsque la commande est relancée.
        demarche.pieces_requises.all().delete()
        PieceRequise.objects.bulk_create([
            PieceRequise(demarche=demarche, libelle=libelle, obligatoire=obligatoire)
            for libelle, obligatoire in pieces
        ])

        # Lien Django vers la fiche officielle et la loi déjà indexée côté IA.
        # Ne pas réinitialiser les relations de sources existantes.
        sources = [
            (
                "Transformer un droit d'occupation en titre foncier - Ministère des Finances",
                URL_FICHE_OFFICIELLE,
                TypeSource.PAGE_WEB,
            ),
            (
                "Loi n° 2017-31 - Cession de terrains domaniaux à usage d'habitation",
                URL_LOI,
                TypeSource.PAGE_WEB,
            ),
        ]
        for titre, url, type_source in sources:
            source, _ = SourceAdministrative.objects.get_or_create(
                url=url,
                defaults={
                    "titre": titre,
                    "type": type_source,
                    "description_courte": (
                        "Conditions et procédure de transformation "
                        "des droits d'occupation"
                    ),
                },
            )
            source.demarches.add(demarche)

        self.stdout.write(self.style.SUCCESS(
            f"Démarche {CODE_DEMARCHE} enregistrée avec "
            f"{len(etapes)} étapes et {len(pieces)} pièces renseignées."
        ))
