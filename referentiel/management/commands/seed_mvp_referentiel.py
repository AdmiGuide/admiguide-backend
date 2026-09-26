from django.core.management.base import BaseCommand
from django.utils import timezone

from referentiel.models import (
    Administration,
    DemarcheAdministrative,
    EtapeDemarche,
    PieceRequise,
    ServiceAdministratif,
    SourceAdministrative,
    StatutSource,
    TypeSource,
)


class Command(BaseCommand):
    """Synchronise les données de référence nécessaires au MVP."""

    help = "Initialise ou met à jour le référentiel MVP d'AdmiGuide."

    def handle(self, *args, **options):
        interieur, _ = Administration.objects.update_or_create(
            nom="Ministère de l'Intérieur et de la Sécurité publique",
            defaults={"sigle": ""},
        )

        dgse, _ = Administration.objects.update_or_create(
            nom="Direction générale des Sénégalais de l'Extérieur",
            defaults={"sigle": "DGSE"},
        )

        pensions, _ = Administration.objects.update_or_create(
            nom="Direction des Pensions",
            defaults={"sigle": ""},
        )

        service_passeports, _ = ServiceAdministratif.objects.update_or_create(
            administration=interieur,
            nom="Service des passeports ou représentation consulaire compétente",
            defaults={
                "adresse": "",
                "contact": "",
            },
        )

        service_dgse, _ = ServiceAdministratif.objects.update_or_create(
            administration=dgse,
            nom="Direction générale des Sénégalais de l'Extérieur",
            defaults={"adresse": "", "contact": ""},
        )

        service_consulaire, _ = ServiceAdministratif.objects.update_or_create(
            administration=dgse,
            nom="Représentation diplomatique ou consulaire du Sénégal",
            defaults={"adresse": "", "contact": ""},
        )

        service_pensions, _ = ServiceAdministratif.objects.update_or_create(
            administration=pensions,
            nom="Direction des Pensions",
            defaults={"adresse": "", "contact": ""},
        )

        self._configurer_passeport_perdu(service_passeports)
        self._configurer_retour_definitif(service_dgse)
        self._configurer_naissance_etranger(service_consulaire)
        self._configurer_deces_fonctionnaire(service_pensions)

        self.stdout.write(
            self.style.SUCCESS(
                "Référentiel MVP synchronisé avec succès."
            )
        )

    def _demarche(self, code, intitule, description, cout, delai):
        """Crée la démarche ou met à jour ses informations principales."""
        demarche, _ = DemarcheAdministrative.objects.update_or_create(
            code=code,
            defaults={
                "intitule": intitule,
                "description": description,
                "cout_indicatif": cout,
                "delai_indicatif": delai,
            },
        )
        return demarche

    def _synchroniser_etapes(self, demarche, descriptions):
        """Synchronise les étapes dans l'ordre attendu."""
        ordres = []

        for ordre, description in enumerate(descriptions, start=1):
            EtapeDemarche.objects.update_or_create(
                demarche=demarche,
                ordre=ordre,
                defaults={"description": description},
            )
            ordres.append(ordre)

        demarche.etapes.exclude(ordre__in=ordres).delete()

    def _synchroniser_pieces(self, demarche, pieces):
        """Remplace les anciennes pièces par la liste actuelle."""
        demarche.pieces_requises.all().delete()

        PieceRequise.objects.bulk_create(
            [
                PieceRequise(
                    demarche=demarche,
                    libelle=libelle,
                    obligatoire=obligatoire,
                )
                for libelle, obligatoire in pieces
            ]
        )

    def _ajouter_source(
        self,
        demarche,
        titre,
        url,
        pays_application=None,
    ):
        """Crée ou actualise une source officielle puis la relie."""

        source, _ = SourceAdministrative.objects.update_or_create(
            url=url,
            defaults={
                "titre": titre,
                "type": TypeSource.PAGE_WEB,
                "statut": StatutSource.DISPONIBLE,
                "pays_application": pays_application,
                "date_consultation": timezone.now(),
            },
        )

        source.demarches.add(demarche)

    def _reinitialiser_relations(self, demarche, services):
        """Retire les anciennes relations susceptibles d'être obsolètes."""
        demarche.services.set(services)
        demarche.sources.clear()

    def _configurer_passeport_perdu(self, service):
        """Configure le remplacement d'un passeport sénégalais perdu."""
        demarche = self._demarche(
            code="REMPLACEMENT_PASSEPORT_PERDU",
            intitule="Remplacement d'un passeport perdu",
            description=(
                "Orientation pour déclarer la perte d'un passeport sénégalais "
                "et préparer son remplacement."
            ),
            cout="Variable selon le lieu de dépôt",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(demarche, [service])

        self._synchroniser_etapes(
            demarche,
            [
                "Déclarer la perte du passeport.",
                "Préparer les pièces justificatives demandées.",
                "Identifier le service compétent et prendre rendez-vous si nécessaire.",
                "Déposer la demande de remplacement.",
                "Retirer le nouveau passeport selon les indications du service.",
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                ("Certificat ou déclaration de perte", True),
                ("Carte nationale d'identité CEDEAO", True),
                ("Justificatif de domicile dans le pays de résidence", False),
                ("Justificatif de paiement ou timbre fiscal selon le service", True),
            ],
        )

        self._ajouter_source(
            demarche,
            "Passeport ordinaire - Ministère de l'Intérieur",
            "https://www.interieur.gouv.sn/services/services-aux-usagers/passeport-ordinaire",
            pays_application="SN",
        )
        
        self._ajouter_source(
            demarche,
            "Renouvellement de passeport - Consulat général du Sénégal à Paris",
            "https://consulsen-paris.gouv.sn/renouvellement-de-passeport/",
            pays_application="FR",
        )

        self._ajouter_source(
            demarche,
            "Renouvellement de passeport - Consulat général du Sénégal à Lyon",
            "https://consulsen-lyon.gouv.sn/renouvellement-de-passeport/",
            pays_application="FR",
        )

    def _configurer_retour_definitif(self, service):
        """Configure le retour définitif au Sénégal."""
        demarche = self._demarche(
            code="RETOUR_EFFETS_PERSONNELS",
            intitule="Retour définitif au Sénégal avec effets personnels",
            description=(
                "Orientation pour préparer un retour définitif au Sénégal "
                "avec des effets personnels."
            ),
            cout="À confirmer auprès du service compétent",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(demarche, [service])
        self._synchroniser_etapes(
            demarche,
            [
                "Vérifier les conditions du certificat de déménagement.",
                "Préparer la liste des biens et les justificatifs demandés.",
                "Demander le certificat auprès du service compétent.",
                "Conserver les documents pour les formalités liées au retour.",
            ],
        )
        self._synchroniser_pieces(
            demarche,
            [
                ("Liste des bagages et biens à déménager en deux exemplaires", True),
                ("Carte consulaire originale datant de plus de six mois", True),
                ("Billet ou réservation pour le retour définitif au Sénégal", True),
            ],
        )
        self._ajouter_source(
            demarche,
            "Certificat de déménagement - DGSE",
            "https://dgse.gouv.sn/content/certificat-de-d%C3%A9m%C3%A9nagement",
        )

    def _configurer_naissance_etranger(self, service):
        """Configure la transcription d'une naissance à l'étranger."""
        demarche = self._demarche(
            code="NAISSANCE_ETRANGER",
            intitule="Transcription d'une naissance survenue à l'étranger",
            description=(
                "Orientation pour faire transcrire au Sénégal un acte de "
                "naissance établi à l'étranger."
            ),
            cout="À confirmer auprès du service compétent",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(demarche, [service])
        self._synchroniser_etapes(
            demarche,
            [
                "Réunir l'acte de naissance étranger et les justificatifs demandés.",
                "Identifier la représentation sénégalaise compétente.",
                "Déposer la demande de transcription.",
                "Suivre le traitement et récupérer l'acte transcrit.",
            ],
        )
        self._synchroniser_pieces(
            demarche,
            [
                ("Deux copies intégrales originales de l'acte de naissance datant de moins de trois mois", True),
                ("Document d'identité sénégalais en cours de validité du père ou de la mère", True),
                ("Livret de famille dans lequel l'enfant est inscrit", True),
            ],
        )
        self._ajouter_source(
            demarche,
            "Transcription d'un acte d'état civil - DGSE",
            "https://dgse.gouv.sn/content/transcription-d%E2%80%99un-acte-d%E2%80%99%C3%A9tat-civil",
        )

    def _configurer_deces_fonctionnaire(self, service):
        """Configure pension et capital-décès."""
        demarche = self._demarche(
            code="DECES_FONCTIONNAIRE",
            intitule="Droits après le décès d'un fonctionnaire en activité",
            description=(
                "Orientation pour préparer les démarches de réversion de pension "
                "et de capital-décès."
            ),
            cout="À confirmer auprès du service compétent",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(demarche, [service])
        self._synchroniser_etapes(
            demarche,
            [
                "Réunir les actes et justificatifs relatifs au décès et aux ayants droit.",
                "Constituer le dossier de pension et de capital-décès.",
                "Déposer le dossier auprès de la Direction des Pensions.",
                "Suivre le traitement du dossier auprès du service compétent.",
            ],
        )
        self._synchroniser_pieces(
            demarche,
            [
                ("Formulaire de demande de liquidation", True),
                ("Demande manuscrite de capital-décès", True),
                ("Acte de naissance du conjoint ou copie légalisée de sa pièce d'identité", True),
                ("Acte de mariage", True),
                ("Acte de décès", True),
                ("Certificat de non-remariage, selon le cas", False),
                ("Certificat de non-séparation", True),
                ("Jugement d'hérédité", True),
                ("Certificat de non-opposition ou de non-appel", True),
                ("Actes de naissance des enfants", True),
                ("Certificat collectif de vie", True),
                ("Acte de tutelle, lorsque nécessaire", False),
                ("Copie légalisée de la pièce d'identité du tuteur", False),
                ("État des services militaires, lorsque applicable", False),
                ("Numéro de pension militaire, lorsque applicable", False),
                ("Justificatifs de validation des services auxiliaires", False),
                ("Acte de radiation", True),
                ("État général des services", True),
                ("Certificat de cessation de paiement", True),
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
