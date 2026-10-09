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

        dgid, _ = Administration.objects.update_or_create(
            nom="Direction générale des Impôts et des Domaines",
            defaults={"sigle": "DGID"},
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
            defaults={
                "adresse": "",
                "contact": "",
            },
        )

        service_consulaire, _ = ServiceAdministratif.objects.update_or_create(
            administration=dgse,
            nom="Représentation diplomatique ou consulaire du Sénégal",
            defaults={
                "adresse": "",
                "contact": "",
            },
        )

        service_pensions, _ = ServiceAdministratif.objects.update_or_create(
            administration=pensions,
            nom="Direction des Pensions",
            defaults={
                "adresse": "",
                "contact": "",
            },
        )

        service_domaines, _ = ServiceAdministratif.objects.update_or_create(
            administration=dgid,
            nom="Bureau des Domaines territorialement compétent",
            defaults={
                "adresse": "",
                "contact": "",
            },
        )

        service_conservation, _ = ServiceAdministratif.objects.update_or_create(
            administration=dgid,
            nom="Conservation de la propriété et des droits fonciers",
            defaults={
                "adresse": "",
                "contact": "",
            },
        )

        self._configurer_passeport_perdu(service_passeports)
        self._configurer_retour_definitif(service_dgse)
        self._configurer_naissance_etranger(service_consulaire)

        # Remplace l'ancienne démarche unique liée au décès
        # par les deux nouvelles démarches.
        self._migrer_ancienne_demarche_deces()

        self._configurer_deces_fonctionnaire_activite(
            service_pensions
        )
        self._configurer_deces_fonctionnaire_retraite(
            service_pensions
        )

        self._configurer_regularisation_bail(
            service_domaines
        )

        self._configurer_acquisition_mutation_titre_foncier(
            service_conservation
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Référentiel MVP synchronisé avec succès."
            )
        )

    def _demarche(
        self,
        code,
        intitule,
        description,
        cout,
        delai,
    ):
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

    def _synchroniser_etapes(
        self,
        demarche,
        descriptions,
    ):
        """Synchronise les étapes dans l'ordre attendu."""

        ordres = []

        for ordre, description in enumerate(descriptions, start=1):
            EtapeDemarche.objects.update_or_create(
                demarche=demarche,
                ordre=ordre,
                defaults={
                    "description": description,
                },
            )

            ordres.append(ordre)

        demarche.etapes.exclude(
            ordre__in=ordres
        ).delete()

    def _synchroniser_pieces(
        self,
        demarche,
        pieces,
    ):
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
    ):
        """Crée ou actualise une source officielle puis la relie."""

        source, _ = SourceAdministrative.objects.update_or_create(
            url=url,
            defaults={
                "titre": titre,
                "type": TypeSource.PAGE_WEB,
                "statut": StatutSource.DISPONIBLE,
                "date_consultation": timezone.now(),
            },
        )

        source.demarches.add(demarche)

    def _reinitialiser_relations(
        self,
        demarche,
        services,
    ):
        """Retire les anciennes relations susceptibles d'être obsolètes."""

        demarche.services.set(services)
        demarche.sources.clear()

    def _migrer_ancienne_demarche_deces(self):
        """
        Remplace l'ancien code DECES_FONCTIONNAIRE
        par le nouveau code correspondant au décès
        d'un fonctionnaire encore en activité.
        """

        ancien_code = "DECES_FONCTIONNAIRE"
        nouveau_code = (
            "REVERSION_PENSION_CAPITAL_DECES_ACTIVITE"
        )

        ancienne = (
            DemarcheAdministrative.objects
            .filter(code=ancien_code)
            .first()
        )

        # Rien à migrer si l'ancienne démarche n'existe pas.
        if not ancienne:
            return

        nouvelle = (
            DemarcheAdministrative.objects
            .filter(code=nouveau_code)
            .first()
        )

        # Si la nouvelle démarche existe déjà,
        # rattache les anciennes orientations à celle-ci.
        if nouvelle:
            ancienne.orientations.update(
                demarche=nouvelle
            )

            ancienne.delete()
            return

        # Sinon, conserve l'enregistrement existant
        # mais remplace simplement son ancien code.
        ancienne.code = nouveau_code
        ancienne.save(
            update_fields=["code"]
        )

    def _configurer_passeport_perdu(
        self,
        service,
    ):
        """Configure le remplacement d'un passeport sénégalais perdu."""

        demarche = self._demarche(
            code="REMPLACEMENT_PASSEPORT_PERDU",
            intitule="Remplacement d'un passeport perdu",
            description=(
                "Orientation pour déclarer la perte d'un passeport "
                "sénégalais et préparer son remplacement."
            ),
            cout="Variable selon le lieu de dépôt",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                "Déclarer la perte du passeport.",
                (
                    "Préparer les pièces justificatives "
                    "demandées."
                ),
                (
                    "Identifier le service compétent et prendre "
                    "rendez-vous si nécessaire."
                ),
                (
                    "Déposer la demande de remplacement."
                ),
                (
                    "Retirer le nouveau passeport selon "
                    "les indications du service."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Certificat ou déclaration de perte",
                    True,
                ),
                (
                    "Carte nationale d'identité CEDEAO",
                    True,
                ),
                (
                    "Justificatif de domicile dans le pays "
                    "de résidence",
                    False,
                ),
                (
                    "Justificatif de paiement ou timbre fiscal "
                    "selon le service",
                    True,
                ),
            ],
        )

        self._ajouter_source(
            demarche,
            "Passeport ordinaire - Ministère de l'Intérieur",
            (
                "https://www.interieur.gouv.sn/services/"
                "services-aux-usagers/passeport-ordinaire"
            ),
        )

    def _configurer_retour_definitif(
        self,
        service,
    ):
        """Configure le retour définitif au Sénégal."""

        demarche = self._demarche(
            code="RETOUR_EFFETS_PERSONNELS",
            intitule=(
                "Retour définitif au Sénégal avec effets personnels"
            ),
            description=(
                "Orientation pour préparer un retour définitif "
                "au Sénégal avec des effets personnels."
            ),
            cout="À confirmer auprès du service compétent",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Vérifier les conditions du certificat "
                    "de déménagement."
                ),
                (
                    "Préparer la liste des biens et les "
                    "justificatifs demandés."
                ),
                (
                    "Demander le certificat auprès du service "
                    "compétent."
                ),
                (
                    "Conserver les documents pour les formalités "
                    "liées au retour."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Liste des bagages et biens à déménager "
                    "en deux exemplaires",
                    True,
                ),
                (
                    "Carte consulaire originale datant "
                    "de plus de six mois",
                    True,
                ),
                (
                    "Billet ou réservation pour le retour "
                    "définitif au Sénégal",
                    True,
                ),
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

    def _configurer_naissance_etranger(
        self,
        service,
    ):
        """Configure la transcription d'une naissance à l'étranger."""

        demarche = self._demarche(
            code="NAISSANCE_ETRANGER",
            intitule=(
                "Transcription d'une naissance survenue à l'étranger"
            ),
            description=(
                "Orientation pour faire transcrire au Sénégal "
                "un acte de naissance établi à l'étranger."
            ),
            cout="À confirmer auprès du service compétent",
            delai="Variable selon le service compétent",
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Réunir l'acte de naissance étranger "
                    "et les justificatifs demandés."
                ),
                (
                    "Identifier la représentation sénégalaise "
                    "compétente."
                ),
                (
                    "Déposer la demande de transcription."
                ),
                (
                    "Suivre le traitement et récupérer "
                    "l'acte transcrit."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Deux copies intégrales originales de l'acte "
                    "de naissance datant de moins de trois mois",
                    True,
                ),
                (
                    "Document d'identité sénégalais en cours "
                    "de validité du père ou de la mère",
                    True,
                ),
                (
                    "Livret de famille dans lequel "
                    "l'enfant est inscrit",
                    True,
                ),
            ],
        )

        self._ajouter_source(
            demarche,
            "Transcription d'un acte d'état civil - DGSE",
            (
                "https://dgse.gouv.sn/content/"
                "transcription-d%E2%80%99un-acte-"
                "d%E2%80%99%C3%A9tat-civil"
            ),
        )

    def _configurer_deces_fonctionnaire_activite(
        self,
        service,
    ):
        """
        Configure la réversion de pension et le capital-décès
        d'un fonctionnaire décédé en activité.
        """

        demarche = self._demarche(
            code="REVERSION_PENSION_CAPITAL_DECES_ACTIVITE",
            intitule=(
                "Réversion de pension et capital-décès "
                "d'un fonctionnaire décédé en activité"
            ),
            description=(
                "Démarche permettant aux ayants-cause d'un "
                "fonctionnaire décédé alors qu'il travaillait "
                "encore de demander la réversion de ses droits "
                "à pension ainsi que le paiement du capital-décès."
            ),
            cout="Gratuit",
            delai="Environ 3 mois pour les décisions",
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Préparer la demande de liquidation de pension "
                    "et la demande manuscrite de capital-décès."
                ),
                (
                    "Réunir les actes et justificatifs relatifs "
                    "au décès, aux ayants-cause et à la carrière "
                    "du fonctionnaire."
                ),
                (
                    "Déposer le dossier auprès de la Direction "
                    "des Pensions."
                ),
                (
                    "Suivre le traitement jusqu'aux décisions "
                    "et à la délivrance de la carte de pension."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Demande de liquidation de pension sur imprimé "
                    "disponible au bureau d'accueil et d'information",
                    True,
                ),
                (
                    "Demande manuscrite pour le capital-décès",
                    True,
                ),
                (
                    "Acte de naissance ou photocopie légalisée "
                    "de la CNI du ou des conjoints survivants",
                    False,
                ),
                (
                    "Acte de mariage",
                    False,
                ),
                (
                    "Acte de décès",
                    True,
                ),
                (
                    "Acte de non-remariage pour les femmes "
                    "âgées de moins de 45 ans",
                    False,
                ),
                (
                    "Acte de non-séparation de corps",
                    False,
                ),
                (
                    "Jugement d'hérédité",
                    True,
                ),
                (
                    "Certificat de non-opposition ni appel",
                    True,
                ),
                (
                    "Actes de naissance des enfants "
                    "mineurs et majeurs",
                    False,
                ),
                (
                    "Certificat de vie collectif des enfants",
                    False,
                ),
                (
                    "Acte de tutelle si la mère n'est pas tutrice",
                    False,
                ),
                (
                    "Photocopie légalisée de la carte d'identité "
                    "du tuteur",
                    False,
                ),
                (
                    "État signalétique des services militaires, "
                    "s'il y a lieu",
                    False,
                ),
                (
                    "Matricule de pension militaire pour les "
                    "titulaires d'une pension militaire",
                    False,
                ),
                (
                    "Justificatifs de validation des services "
                    "auxiliaires, lorsque cela s'applique",
                    False,
                ),
                (
                    "Acte de radiation",
                    True,
                ),
                (
                    "Relevé général des services",
                    True,
                ),
                (
                    "Certificat de cessation de paiement "
                    "du fonctionnaire",
                    True,
                ),
            ],
        )

        self._ajouter_source(
            demarche,
            (
                "Réversion de la pension et capital-décès "
                "- Direction des Pensions"
            ),
            (
                "https://budget.sec.gouv.sn/consulter-l-article/"
                "demander-la-reversion-de-la-pension-et-le-"
                "capital-deces-pour-un-fonctionnaire-decede-"
                "en-activite"
            ),
        )

    def _configurer_deces_fonctionnaire_retraite(
        self,
        service,
    ):
        """
        Configure la réversion de pension d'un fonctionnaire
        décédé après son départ à la retraite.
        """

        demarche = self._demarche(
            code="REVERSION_PENSION_APRES_RETRAITE",
            intitule=(
                "Réversion de pension d'un fonctionnaire "
                "décédé après la retraite"
            ),
            description=(
                "Démarche permettant aux ayants-cause d'un "
                "ancien fonctionnaire déjà retraité au moment "
                "de son décès de demander la réversion "
                "de sa pension."
            ),
            cout="Gratuit",
            delai=(
                "Environ 3 mois pour la décision de concession"
            ),
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Préparer la demande de liquidation de pension."
                ),
                (
                    "Réunir les actes et justificatifs relatifs "
                    "au décès et aux ayants-cause."
                ),
                (
                    "Joindre la carte ou le bulletin de pension "
                    "du défunt et déposer le dossier auprès "
                    "de la Direction des Pensions."
                ),
                (
                    "Suivre le traitement jusqu'à la décision "
                    "et à la délivrance de la carte de pension."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Demande de liquidation de pension sur imprimé "
                    "disponible au bureau d'accueil et d'information",
                    True,
                ),
                (
                    "Acte de naissance ou photocopie légalisée "
                    "de la CNI du ou des conjoints survivants",
                    False,
                ),
                (
                    "Acte de mariage",
                    False,
                ),
                (
                    "Acte de non-divorce et de non-remariage "
                    "si la veuve est âgée de moins de 45 ans",
                    False,
                ),
                (
                    "Acte de décès en deux exemplaires",
                    True,
                ),
                (
                    "Jugement d'hérédité",
                    True,
                ),
                (
                    "Certificat de non-opposition ni appel",
                    True,
                ),
                (
                    "Actes de naissance des enfants "
                    "mineurs et majeurs",
                    False,
                ),
                (
                    "Certificat de vie collectif des enfants",
                    False,
                ),
                (
                    "Acte de tutelle si la mère n'est pas tutrice "
                    "ou si les enfants ne sont pas à sa charge",
                    False,
                ),
                (
                    "Photocopie légalisée de la carte d'identité "
                    "du tuteur",
                    False,
                ),
                (
                    "Carte ou bulletin de pension du défunt",
                    True,
                ),
            ],
        )

        self._ajouter_source(
            demarche,
            (
                "Réversion d'une pension après la retraite "
                "- Direction des Pensions"
            ),
            (
                "https://budget.sec.gouv.sn/consulter-l-article/"
                "demander-la-reversion-d-une-pension-de-retraite-"
                "pour-un-fonctionnaire-decede-apres-la-retraite"
            ),
        )


    def _configurer_regularisation_bail(
        self,
        service,
    ):
        """Configure la régularisation foncière par voie de bail."""

        demarche = self._demarche(
            code="REGULARISATION_BAIL",
            intitule="Régularisation par voie de bail",
            description=(
                "Démarche permettant à une personne physique "
                "ou morale d'obtenir un bail sur un terrain "
                "qu'elle occupe ou qu'elle a identifié et qui "
                "dépend du domaine privé de l'État."
            ),
            cout="À confirmer auprès du service compétent",
            delai="À confirmer auprès du service compétent",
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Préparer la demande de régularisation "
                    "par voie de bail."
                ),
                (
                    "Réunir les pièces demandées et les préparer "
                    "en cinq exemplaires."
                ),
                (
                    "Déposer le dossier auprès du bureau des "
                    "Domaines territorialement compétent."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Demande de régularisation par voie de bail",
                    True,
                ),
                (
                    "Photocopie du titre ou de la délibération",
                    True,
                ),
                (
                    "Photocopie du plan de masse",
                    True,
                ),
                (
                    "Photocopie du plan de situation",
                    True,
                ),
                (
                    "Photocopie de la carte nationale d'identité",
                    True,
                ),
                (
                    "Acte de vente enregistré",
                    True,
                ),
            ],
        )

        self._ajouter_source(
            demarche,
            "Régularisation par voie de bail - DGID",
            "https://www.dgid.sn/fiches/regularisation-bail",
        )


    def _configurer_acquisition_mutation_titre_foncier(
        self,
        service,
    ):
        """
        Configure l'acquisition et la mutation
        d'un bien déjà sous titre foncier.
        """

        demarche = self._demarche(
            code="ACQUISITION_MUTATION_TITRE_FONCIER",
            intitule=(
                "Acquisition et mutation d'un bien "
                "sous titre foncier"
            ),
            description=(
                "Démarche concernant l'acquisition d'un immeuble "
                "qui possède déjà un titre foncier et appartient "
                "à un particulier, jusqu'à l'inscription du droit "
                "de l'acquéreur au livre foncier."
            ),
            cout=(
                "État de droits réels : généralement 500 à 1 500 FCFA ; "
                "autres droits et taxes auprès du notaire"
            ),
            delai=(
                "Délai réglementaire maximal de 30 jours ; "
                "état de droits réels délivré en 3 jours"
            ),
        )

        self._reinitialiser_relations(
            demarche,
            [service],
        )

        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Demander au Conservateur un état de droits "
                    "réels sur l'immeuble."
                ),
                (
                    "Effectuer la déclaration préalable de "
                    "transaction auprès du Directeur chargé "
                    "des Domaines."
                ),
                (
                    "Faire établir et signer l'acte de vente "
                    "par le notaire avec l'acheteur et le vendeur."
                ),
                (
                    "Le notaire transmet le dossier à la "
                    "Conservation foncière pour l'enregistrement "
                    "et la publicité foncière."
                ),
                (
                    "Faire constater la mutation du bien au nom "
                    "de l'acquéreur par un nouvel état de "
                    "droits réels."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Copie du titre foncier "
                    "(pour la demande d'état de droits réels)",
                    True,
                ),
                (
                    "Copie de la carte nationale d'identité "
                    "(pour la demande d'état de droits réels)",
                    True,
                ),
            ],
        )

        self._ajouter_source(
            demarche,
            "Régularisation d'un titre foncier (TF) - DGID",
            "https://www.dgid.sn/fiches/regularisation-tf",
        )

        self._ajouter_source(
            demarche,
            "État de droits réels - DGID",
            "https://www.dgid.sn/fiches/etat-droits-reels",
        )