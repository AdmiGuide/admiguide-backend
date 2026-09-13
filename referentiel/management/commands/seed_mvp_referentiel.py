from django.core.management.base import BaseCommand
from django.utils import timezone

from referentiel.models import (
    Administration,
    DemarcheAdministrative,
    PieceRequise,
    ServiceAdministratif,
    SourceAdministrative,
    StatutSource,
    TypeSource,
)


class Command(BaseCommand):
    """Ajoute les données de référence nécessaires au MVP."""

    help = "Initialise le référentiel MVP d'AdmiGuide."

    def handle(self, *args, **options):
        # Administrations utilisées par les nouvelles démarches.
        dgse, _ = Administration.objects.get_or_create(
            nom="Direction générale des Sénégalais de l'Extérieur",
            defaults={"sigle": "DGSE"},
        )

        pensions, _ = Administration.objects.get_or_create(
            nom="Direction des Pensions",
        )

        # Services compétents.
        service_dgse, _ = ServiceAdministratif.objects.get_or_create(
            administration=dgse,
            nom="Direction générale des Sénégalais de l'Extérieur",
        )

        service_consulaire, _ = ServiceAdministratif.objects.get_or_create(
            administration=dgse,
            nom="Représentation diplomatique ou consulaire du Sénégal",
        )

        service_pensions, _ = ServiceAdministratif.objects.get_or_create(
            administration=pensions,
            nom="Direction des Pensions",
        )

        # Configure les trois démarches du MVP.
        self._configurer_retour_definitif(service_dgse)
        self._configurer_naissance_etranger(service_consulaire)
        self._configurer_deces_fonctionnaire(service_pensions)

        self.stdout.write(
            self.style.SUCCESS(
                "Référentiel MVP initialisé avec succès."
            )
        )

    def _ajouter_pieces(self, demarche, pieces):
        """Ajoute les pièces sans créer de doublons."""

        for libelle in pieces:
            PieceRequise.objects.get_or_create(
                demarche=demarche,
                libelle=libelle,
                defaults={"obligatoire": True},
            )

    def _ajouter_source(self, demarche, titre, url):
        """Crée la source officielle et la relie à la démarche."""

        source, _ = SourceAdministrative.objects.get_or_create(
            url=url,
            defaults={
                "titre": titre,
                "type": TypeSource.PAGE_WEB,
                "statut": StatutSource.DISPONIBLE,
                "date_consultation": timezone.now(),
            },
        )

        source.demarches.add(demarche)

    def _configurer_retour_definitif(self, service):
        """Configure le retour définitif au Sénégal."""

        demarche = DemarcheAdministrative.objects.get(
            code="RETOUR_EFFETS_PERSONNELS"
        )

        demarche.services.add(service)

        self._ajouter_pieces(
            demarche,
            [
                "Liste des bagages et biens à déménager en deux exemplaires",
                "Carte consulaire originale datant de plus de six mois",
                "Billet ou réservation pour le retour définitif au Sénégal",
            ],
        )

        self._ajouter_source(
            demarche,
            "Certificat de déménagement - DGSE",
            (
                "https://dgse.gouv.sn/content/"
                "certificat-de-d%C3%A9m%C3%A9nagement"
            ),
        )

    def _configurer_naissance_etranger(self, service):
        """Configure la transcription d'une naissance à l'étranger."""

        demarche = DemarcheAdministrative.objects.get(
            code="NAISSANCE_ETRANGER"
        )

        demarche.services.add(service)

        self._ajouter_pieces(
            demarche,
            [
                (
                    "Deux copies intégrales originales de l'acte de naissance "
                    "datant de moins de trois mois"
                ),
                (
                    "Document d'identité sénégalais en cours de validité "
                    "du père ou de la mère"
                ),
                "Livret de famille dans lequel l'enfant est inscrit",
            ],
        )

        self._ajouter_source(
            demarche,
            "Transcription d'un acte d'état civil - DGSE",
            (
                "https://dgse.gouv.sn/content/"
                "transcription-d%E2%80%99un-acte-d%E2%80%99%C3%A9tat-civil"
            ),
        )

    def _configurer_deces_fonctionnaire(self, service):
        """Configure pension et capital-décès."""

        demarche = DemarcheAdministrative.objects.get(
            code="DECES_FONCTIONNAIRE"
        )

        demarche.services.add(service)

        self._ajouter_pieces(
            demarche,
            [
                "Formulaire de demande de liquidation",
                "Demande manuscrite de capital-décès",
                (
                    "Acte de naissance du conjoint ou copie légalisée "
                    "de sa pièce d'identité"
                ),
                "Acte de mariage",
                "Acte de décès",
                "Certificat de non-remariage, selon le cas",
                "Certificat de non-séparation",
                "Jugement d'hérédité",
                "Certificat de non-opposition ou de non-appel",
                "Actes de naissance des enfants",
                "Certificat collectif de vie",
                "Acte de tutelle, lorsque nécessaire",
                "Copie légalisée de la pièce d'identité du tuteur",
                "État des services militaires, lorsque applicable",
                "Numéro de pension militaire, lorsque applicable",
                "Justificatifs de validation des services auxiliaires",
                "Acte de radiation",
                "État général des services",
                "Certificat de cessation de paiement",
            ],
        )

        self._ajouter_source(
            demarche,
            "Réversion de pension et capital-décès - Direction des Pensions",
            (
                "https://budget.sec.gouv.sn/consulter-l-article/"
                "demander-la-reversion-de-la-pension-et-le-capital-deces-"
                "pour-un-fonctionnaire-decede-en-activite"
            ),
        )