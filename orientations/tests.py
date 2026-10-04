from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from referentiel.models import (
    DemarcheAdministrative,
    EtapeDemarche,
)

from .models import (
    OrientationAdministrative,
    QuestionComplementaire,
    ReponseComplementaire,
    SituationAdministrative,
    SuiviEtape,
)

from .services.orientation_service import (
    MVP_DEMARCHE_CODES,
    analyser_et_enregistrer,
)


User = get_user_model()


class SuiviEtapeAPITest(APITestCase):
    """Teste le suivi des étapes d'une feuille de route."""

    def setUp(self):
        """Prépare les données nécessaires aux tests."""

        self.user = User.objects.create_user(
            email="dado@test.com",
            password="Test1234!",
            nom_complet="Dado Test",
        )

        self.autre_user = User.objects.create_user(
            email="autre@test.com",
            password="Test1234!",
            nom_complet="Autre Utilisateur",
        )

        # Démarche principale.
        self.demarche = DemarcheAdministrative.objects.create(
            code="TEST_DEMARCHE",
            intitule="Démarche de test",
            description="Démarche utilisée pour les tests.",
        )

        self.etape1 = EtapeDemarche.objects.create(
            demarche=self.demarche,
            ordre=1,
            description="Première étape",
        )

        self.etape2 = EtapeDemarche.objects.create(
            demarche=self.demarche,
            ordre=2,
            description="Deuxième étape",
        )

        self.situation = SituationAdministrative.objects.create(
            utilisateur=self.user,
            description_initiale="Situation administrative de test.",
        )

        self.orientation = OrientationAdministrative.objects.create(
            situation=self.situation,
            demarche=self.demarche,
            resume="Orientation de test.",
        )

        self.client.force_authenticate(user=self.user)

    def get_url(self, etape):
        """Retourne l'URL permettant de modifier une étape."""

        return reverse(
            "situation-etape-update",
            kwargs={
                "public_id": self.situation.public_id,
                "etape_id": etape.id,
            },
        )

    def test_cocher_une_etape(self):
        """Un utilisateur peut terminer une étape."""

        response = self.client.patch(
            self.get_url(self.etape1),
            {"terminee": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["terminee"]
        )

        self.assertEqual(
            response.data["progression"],
            {
                "terminees": 1,
                "total": 2,
                "pourcentage": 50,
            },
        )

        suivi = SuiviEtape.objects.get(
            orientation=self.orientation,
            etape=self.etape1,
        )

        self.assertTrue(
            suivi.terminee
        )

    def test_decocher_une_etape(self):
        """Une étape terminée peut être décochée."""

        SuiviEtape.objects.create(
            orientation=self.orientation,
            etape=self.etape1,
            terminee=True,
        )

        response = self.client.patch(
            self.get_url(self.etape1),
            {"terminee": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["terminee"]
        )

        self.assertEqual(
            response.data["progression"]["pourcentage"],
            0,
        )

    def test_progression_avec_deux_etapes(self):
        """La progression évolue lorsque plusieurs étapes sont cochées."""

        self.client.patch(
            self.get_url(self.etape1),
            {"terminee": True},
            format="json",
        )

        response = self.client.patch(
            self.get_url(self.etape2),
            {"terminee": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["progression"],
            {
                "terminees": 2,
                "total": 2,
                "pourcentage": 100,
            },
        )

    def test_interdire_modification_autre_utilisateur(self):
        """
        Un utilisateur ne peut pas modifier
        la feuille de route d'un autre.
        """

        self.client.force_authenticate(
            user=self.autre_user
        )

        response = self.client.patch(
            self.get_url(self.etape1),
            {"terminee": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_refuser_etape_autre_demarche(self):
        """Une étape étrangère à la démarche doit être refusée."""

        autre_demarche = DemarcheAdministrative.objects.create(
            code="AUTRE_DEMARCHE",
            intitule="Autre démarche",
            description="Autre démarche de test.",
        )

        autre_etape = EtapeDemarche.objects.create(
            demarche=autre_demarche,
            ordre=1,
            description="Étape étrangère",
        )

        response = self.client.patch(
            self.get_url(autre_etape),
            {"terminee": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class PensionsDecesOrientationTest(APITestCase):
    """
    Teste l'intégration Django du domaine PENSIONS_DECES.

    Le service IA est simulé pour que les tests Django
    ne dépendent pas de Groq ni d'une connexion réseau.
    """

    def setUp(self):
        """Crée le référentiel minimal attendu par le service."""

        self.demarche_activite = (
            DemarcheAdministrative.objects.create(
                code=(
                    "REVERSION_PENSION_"
                    "CAPITAL_DECES_ACTIVITE"
                ),
                intitule=(
                    "Réversion de pension et capital-décès "
                    "d'un fonctionnaire décédé en activité"
                ),
                description=(
                    "Démarche pour un fonctionnaire "
                    "décédé en activité."
                ),
            )
        )

        self.demarche_retraite = (
            DemarcheAdministrative.objects.create(
                code="REVERSION_PENSION_APRES_RETRAITE",
                intitule=(
                    "Réversion de pension d'un fonctionnaire "
                    "décédé après la retraite"
                ),
                description=(
                    "Démarche pour un ancien fonctionnaire "
                    "déjà retraité."
                ),
            )
        )

        # Les autres codes sont nécessaires car
        # OrientationService vérifie que le référentiel MVP
        # est complet avant d'appeler l'IA.
        DemarcheAdministrative.objects.create(
            code="REMPLACEMENT_PASSEPORT_PERDU",
            intitule="Remplacement passeport perdu",
            description="Test.",
        )

        DemarcheAdministrative.objects.create(
            code="RETOUR_EFFETS_PERSONNELS",
            intitule="Retour effets personnels",
            description="Test.",
        )

        DemarcheAdministrative.objects.create(
            code="NAISSANCE_ETRANGER",
            intitule="Naissance à l'étranger",
            description="Test.",
        )

    @patch(
        "orientations.services.orientation_service."
        "analyser_situation"
    )
    def test_deces_fonctionnaire_situation_a_preciser(
        self,
        mock_analyser,
    ):
        """
        Une situation ambiguë doit créer
        une question complémentaire.
        """

        mock_analyser.return_value = {
            "statut": "PRECISIONS_REQUISES",
            "questions": [
                {
                    "texte": (
                        "Au moment de son décès, la personne "
                        "travaillait-elle encore comme "
                        "fonctionnaire ou avait-elle déjà "
                        "pris sa retraite ?"
                    ),
                    "type_question": "CHOIX_UNIQUE",
                    "options": [
                        (
                            "Elle travaillait encore "
                            "comme fonctionnaire"
                        ),
                        "Elle était déjà à la retraite",
                        "Je ne sais pas",
                    ],
                }
            ],
        }

        situation = SituationAdministrative.objects.create(
            description_initiale=(
                "Mon père était fonctionnaire et il est décédé. "
                "Je souhaite savoir quelle démarche effectuer "
                "concernant sa pension."
            )
        )

        resultat = analyser_et_enregistrer(
            situation
        )

        self.assertEqual(
            resultat["statut"],
            "PRECISIONS_REQUISES",
        )

        question = situation.questions.get()

        self.assertEqual(
            question.texte,
            (
                "Au moment de son décès, la personne "
                "travaillait-elle encore comme fonctionnaire "
                "ou avait-elle déjà pris sa retraite ?"
            ),
        )

        self.assertEqual(
            question.type_question,
            "CHOIX_UNIQUE",
        )

        self.assertEqual(
            question.options,
            [
                (
                    "Elle travaillait encore "
                    "comme fonctionnaire"
                ),
                "Elle était déjà à la retraite",
                "Je ne sais pas",
            ],
        )

        donnees_envoyees = (
            mock_analyser.call_args.kwargs
        )

        self.assertEqual(
            donnees_envoyees["reponses"],
            [],
        )

        self.assertCountEqual(
            donnees_envoyees["demarche_codes"],
            MVP_DEMARCHE_CODES,
        )

    @patch(
        "orientations.services.orientation_service."
        "analyser_situation"
    )
    def test_orientation_apres_retraite(
        self,
        mock_analyser,
    ):
        """
        La réponse indiquant que le défunt était retraité
        doit permettre d'enregistrer la démarche retraite.
        """

        situation = SituationAdministrative.objects.create(
            description_initiale=(
                "Mon père était fonctionnaire et il est décédé. "
                "Je souhaite savoir quelle démarche effectuer "
                "concernant sa pension."
            )
        )

        question = QuestionComplementaire.objects.create(
            situation=situation,
            texte=(
                "Au moment de son décès, la personne "
                "travaillait-elle encore comme fonctionnaire "
                "ou avait-elle déjà pris sa retraite ?"
            ),
            type_question="CHOIX_UNIQUE",
            options=[
                (
                    "Elle travaillait encore "
                    "comme fonctionnaire"
                ),
                "Elle était déjà à la retraite",
                "Je ne sais pas",
            ],
            ordre=1,
        )

        ReponseComplementaire.objects.create(
            question=question,
            contenu="Elle était déjà à la retraite",
        )

        mock_analyser.return_value = {
            "statut": "ORIENTATION",
            "demarche_code": (
                "REVERSION_PENSION_APRES_RETRAITE"
            ),
            "resume": (
                "Le père de l'utilisateur était fonctionnaire "
                "et était déjà à la retraite au moment "
                "de son décès."
            ),
            "avertissement": "",
        }

        resultat = analyser_et_enregistrer(
            situation
        )

        self.assertEqual(
            resultat["statut"],
            "ORIENTATION",
        )

        self.assertEqual(
            resultat["demarche_code"],
            "REVERSION_PENSION_APRES_RETRAITE",
        )

        situation.refresh_from_db()

        self.assertEqual(
            situation.orientation.demarche.code,
            "REVERSION_PENSION_APRES_RETRAITE",
        )

        donnees_envoyees = (
            mock_analyser.call_args.kwargs
        )

        self.assertEqual(
            donnees_envoyees["reponses"],
            [
                {
                    "texte_question": question.texte,
                    "contenu": (
                        "Elle était déjà à la retraite"
                    ),
                }
            ],
        )

    @patch(
        "orientations.services.orientation_service."
        "analyser_situation"
    )
    def test_orientation_fonctionnaire_en_activite(
        self,
        mock_analyser,
    ):
        """
        Une situation déjà claire doit enregistrer
        directement la démarche du fonctionnaire en activité.
        """

        mock_analyser.return_value = {
            "statut": "ORIENTATION",
            "demarche_code": (
                "REVERSION_PENSION_"
                "CAPITAL_DECES_ACTIVITE"
            ),
            "resume": (
                "Le mari de l'utilisateur était fonctionnaire "
                "et était encore en activité au moment "
                "de son décès."
            ),
            "avertissement": "",
        }

        situation = SituationAdministrative.objects.create(
            description_initiale=(
                "Mon mari était fonctionnaire et travaillait "
                "encore dans l'administration au moment "
                "de son décès. Je souhaite savoir quelle "
                "démarche effectuer."
            )
        )

        resultat = analyser_et_enregistrer(
            situation
        )

        self.assertEqual(
            resultat["statut"],
            "ORIENTATION",
        )

        self.assertEqual(
            resultat["demarche_code"],
            (
                "REVERSION_PENSION_"
                "CAPITAL_DECES_ACTIVITE"
            ),
        )

        situation.refresh_from_db()

        self.assertEqual(
            situation.orientation.demarche.code,
            (
                "REVERSION_PENSION_"
                "CAPITAL_DECES_ACTIVITE"
            ),
        )

        self.assertFalse(
            situation.questions.exists()
        )

        donnees_envoyees = (
            mock_analyser.call_args.kwargs
        )

        self.assertEqual(
            donnees_envoyees["reponses"],
            [],
        )