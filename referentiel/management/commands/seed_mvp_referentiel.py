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
            nom="Commissariat de police dont relève le domicile",
            defaults={
                "adresse": "Dakar - selon le domicile du demandeur",
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

        self._supprimer_ancienne_demarche_passeport()

        self._configurer_demande_passeport(
            service_passeports
        )

        self._configurer_renouvellement_passeport(
            service_passeports
        )

        self._configurer_passeport_perdu_ou_vole(
            service_passeports
        )

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

        self._configurer_transformation_bail_titre_foncier(
            service_domaines
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
        source_type=TypeSource.PAGE_WEB,
        description_courte="",
    ):
        """
        Crée ou actualise une source officielle
        puis la relie à une démarche.
        """

        source, _ = SourceAdministrative.objects.update_or_create(
            url=url,
            defaults={
                "titre": titre,
                "description_courte": description_courte,
                "type": source_type,
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

    def _supprimer_ancienne_demarche_passeport(
    self,
    ):
        """
        Supprime l'ancienne démarche passeport devenue obsolète.

        Les anciennes situations et orientations de développement
        ayant été supprimées, aucune migration n'est nécessaire.
        """

        DemarcheAdministrative.objects.filter(
            code="REMPLACEMENT_PASSEPORT_PERDU"
        ).delete()

        # Supprime également l'ancien service générique
        # s'il n'est plus utilisé par aucune démarche.
        ancien_service = (
            ServiceAdministratif.objects
            .filter(
                nom="Service des passeports"
            )
            .first()
        )

        if (
            ancien_service
            and not ancien_service.demarches.exists()
        ):
            ancien_service.delete()


    def _configurer_demande_passeport(
        self,
        service,
    ):
        """Configure la première demande de passeport à Dakar."""

        demarche = self._demarche(
            code="DEMANDE_PASSEPORT_ORDINAIRE",
            intitule="Demande d'un passeport ordinaire",
            description=(
                "Démarche permettant à un citoyen sénégalais "
                "résidant à Dakar de demander un passeport ordinaire."
            ),
            cout="20 000 FCFA",
            delai=(
                "Délivrance : 2 semaines ; "
                "rendez-vous à Dakar : 2 à 25 jours"
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
                    "Préparer les pièces nécessaires "
                    "à la demande de passeport."
                ),
                (
                    "Payer 20 000 FCFA auprès de la Direction "
                    "de l'Enregistrement, des Domaines et du Timbre "
                    "et obtenir la quittance."
                ),
                (
                    "Prendre rendez-vous pour le dépôt à Dakar "
                    "en utilisant le numéro de la quittance."
                ),
                (
                    "Déposer le dossier au commissariat de police "
                    "dont relève le domicile."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Original de la carte nationale d'identité",
                    True,
                ),
                (
                    "Copie certifiée conforme de la carte "
                    "nationale d'identité",
                    True,
                ),
                (
                    "Trois photos d'identité en couleur",
                    True,
                ),
                (
                    "Quittance de paiement de 20 000 FCFA",
                    True,
                ),
                (
                    "Autorisation parentale pour un mineur",
                    False,
                ),
                (
                    "Copie certifiée conforme de la CNI "
                    "du père ou de la mère pour un mineur",
                    False,
                ),
                (
                    "Certificat de prise en charge délivré "
                    "par la mairie ou la justice pour un mineur",
                    False,
                ),
                (
                    "Extrait de naissance de moins de trois mois "
                    "à la place de la CNI pour un enfant "
                    "de moins de 5 ans",
                    False,
                ),
                (
                    "Carte d'étudiant valide ou certificat "
                    "de scolarité pour bénéficier du traitement "
                    "prioritaire",
                    False,
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

        self._ajouter_source(
            demarche,
            "Demander un passeport numérisé - e-Sénégal",
            (
                "https://e-senegal.sn/#/comprendre-ma-demarche/"
                "demarche/demander-un-passeport-numerise"
            ),
        )


    def _configurer_renouvellement_passeport(
        self,
        service,
    ):
        """Configure le renouvellement d'un passeport à Dakar."""

        demarche = self._demarche(
            code="RENOUVELLEMENT_PASSEPORT",
            intitule="Renouvellement d'un passeport",
            description=(
                "Démarche permettant à un particulier résidant "
                "à Dakar de renouveler son passeport sénégalais."
            ),
            cout="20 000 FCFA",
            delai=(
                "Délivrance : 2 semaines ; "
                "rendez-vous à Dakar : 2 à 25 jours"
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
                    "Payer 20 000 FCFA auprès de la Direction "
                    "de l'Enregistrement, des Domaines et du Timbre "
                    "et obtenir la quittance."
                ),
                (
                    "Préparer l'ancien passeport, sa copie "
                    "et la quittance de paiement."
                ),
                (
                    "Prendre rendez-vous pour le dépôt à Dakar "
                    "en utilisant le numéro de la quittance."
                ),
                (
                    "Déposer le dossier au commissariat de police "
                    "dont relève le domicile."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Ancien passeport",
                    True,
                ),
                (
                    "Copie de l'ancien passeport",
                    True,
                ),
                (
                    "Quittance de paiement de 20 000 FCFA",
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

        self._ajouter_source(
            demarche,
            "Demander un passeport numérisé - e-Sénégal",
            (
                "https://e-senegal.sn/#/comprendre-ma-demarche/"
                "demarche/demander-un-passeport-numerise"
            ),
        )

        self._ajouter_source(
            demarche,
            "Renouvellement de passeport - DGSE",
            "https://dgse.gouv.sn/content/renouvellement-de-passeport",
        )


    def _configurer_passeport_perdu_ou_vole(
        self,
        service,
    ):
        """Configure le parcours d'un passeport perdu ou volé à Dakar."""

        demarche = self._demarche(
            code="PASSEPORT_PERDU_OU_VOLE",
            intitule="Passeport perdu ou volé",
            description=(
                "Démarche permettant à un particulier résidant "
                "à Dakar de refaire son passeport sénégalais "
                "après une perte ou un vol."
            ),
            cout="20 000 FCFA",
            delai=(
                "Délivrance : 2 semaines ; "
                "rendez-vous à Dakar : 2 à 25 jours"
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
                    "Déclarer la perte ou le vol auprès "
                    "d'un commissariat de police et obtenir "
                    "l'attestation correspondante."
                ),
                (
                    "Payer 20 000 FCFA auprès de la Direction "
                    "de l'Enregistrement, des Domaines et du Timbre "
                    "et obtenir la quittance."
                ),
                (
                    "Préparer les pièces nécessaires pour refaire "
                    "la demande de passeport."
                ),
                (
                    "Prendre rendez-vous pour le dépôt à Dakar "
                    "en utilisant le numéro de la quittance."
                ),
                (
                    "Déposer le nouveau dossier au commissariat "
                    "de police dont relève le domicile."
                ),
            ],
        )

        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Attestation de perte ou de vol délivrée "
                    "par un commissariat de police",
                    True,
                ),
                (
                    "Original de la carte nationale d'identité",
                    True,
                ),
                (
                    "Copie certifiée conforme de la carte "
                    "nationale d'identité",
                    True,
                ),
                (
                    "Trois photos d'identité en couleur",
                    True,
                ),
                (
                    "Quittance de paiement de 20 000 FCFA",
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

        self._ajouter_source(
            demarche,
            "Demander un passeport numérisé - e-Sénégal",
            (
                "https://e-senegal.sn/#/comprendre-ma-demarche/"
                "demarche/demander-un-passeport-numerise"
            ),
        )

        self._ajouter_source(
            demarche,
            "Renouvellement de passeport - DGSE",
            "https://dgse.gouv.sn/content/renouvellement-de-passeport",
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

   
    def _configurer_transformation_bail_titre_foncier(
        self,
        service,
    ):
        """
        Configure la transformation d'un bail existant
        en titre foncier pour un terrain domanial
        à usage d'habitation.
        """

        demarche = self._demarche(
            code="TRANSFORMATION_BAIL_EN_TITRE_FONCIER",
            intitule="Transformer un bail en titre foncier",
            description=(
                "Démarche permettant au titulaire d'un bail "
                "sur un terrain domanial à usage d'habitation "
                "de demander la cession définitive du terrain "
                "et son inscription en pleine propriété "
                "au Livre foncier."
            ),
            cout=(
                "Cession gratuite et exonérée de droits et taxes ; "
                "frais possibles pour certains documents annexes"
            ),
            delai=(
                "Environ 3 mois pour l'acte de cession définitive"
            ),
        )

        # Le point d'entrée principal est le Bureau
        # des Domaines territorialement compétent.
        self._reinitialiser_relations(
            demarche,
            [service],
        )

        # Étapes principales de la procédure.
        self._synchroniser_etapes(
            demarche,
            [
                (
                    "Préparer et déposer la demande de cession "
                    "définitive auprès du Bureau des Domaines "
                    "territorialement compétent."
                ),
                (
                    "Joindre les documents permettant d'établir "
                    "le bail et les droits détenus sur le terrain."
                ),
                (
                    "Faire vérifier les conditions d'éligibilité "
                    "du dossier, notamment la qualité d'attributaire "
                    "et la mise en valeur du terrain."
                ),
                (
                    "Faire constater la mise en valeur du terrain "
                    "par les services compétents du Cadastre."
                ),
                (
                    "Faire procéder au bornage lorsque la situation "
                    "de la parcelle le nécessite."
                ),
                (
                    "Le Bureau des Domaines transmet le dossier "
                    "au Directeur chargé des Domaines pour la suite "
                    "de l'instruction."
                ),
                (
                    "Le dossier est examiné par la Commission "
                    "de contrôle des opérations domaniales."
                ),
                (
                    "Après avis favorable, le transfert en pleine "
                    "propriété est prononcé par arrêté du ministre "
                    "chargé des Domaines."
                ),
                (
                    "Faire inscrire le nouveau droit de propriété "
                    "au Livre foncier."
                ),
                (
                    "Retirer la copie originale du titre foncier "
                    "auprès du Conservateur compétent."
                ),
            ],
        )

        # Pièces nécessaires ou conditionnelles.
        self._synchroniser_pieces(
            demarche,
            [
                (
                    "Demande de cession définitive",
                    True,
                ),
                (
                    "État de droits réels et/ou certificat "
                    "permettant d'établir les droits sur le terrain",
                    True,
                ),
                (
                    "Document justifiant le bail ou le droit "
                    "d'usage détenu sur le terrain",
                    True,
                ),
                (
                    "Jugement d'hérédité avec certificat "
                    "de non-opposition ni appel, si l'attributaire "
                    "est décédé",
                    False,
                ),
                (
                    "Certificat de paiement des droits de mutation "
                    "par décès, si l'attributaire est décédé",
                    False,
                ),
                (
                    "Acte de partage homologué, lorsqu'il existe",
                    False,
                ),
            ],
        )

        # définit notamment le principe de cession gratuite.
        self._ajouter_source(
        demarche,
        "Loi n°2017-31",
        (
            "https://www.dri.gouv.sn/"
            "loi-n%C2%B0-201731-du-15-juillet-2017"
        ),
        source_type=TypeSource.PAGE_WEB,
        description_courte=(
            "Base juridique de la cession gratuite"
        ),
    )

        self._ajouter_source(
            demarche,
            "Décret n°2018-830",
            (
                "https://www.dgid.sn/storage/docs/"
                "D%C3%A9cret%20d_application%20n%202018-830%20"
                "%20autorisant%20la%20cession%20de-finitive%20"
                "et%20a-%20titre%20gratuit%20de%20terrains%20"
                "domaniaux%20a-%20usage%20d_habitation%5B1%5D.pdf"
            ),
            source_type=TypeSource.DOCUMENT,
            description_courte=(
                "Procédure de cession définitive du terrain"
            ),
        )

        self._ajouter_source(
            demarche,
            "Magazine ID n°32 - DGID",
            (
                "https://www.dgid.sn/storage/magazine/"
                "id-magazine-32-juil-sept-2022.pdf"
            ),
            source_type=TypeSource.DOCUMENT,
            description_courte=(
                "Constat de mise en valeur et bornage"
            ),
        )