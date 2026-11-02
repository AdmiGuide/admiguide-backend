
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from orientations.models import (
    SituationAdministrative,
    OrientationAdministrative,
    QuestionComplementaire,
)
from referentiel.models import DemarcheAdministrative


class ChatAccessTests(TestCase):
    """Vérifie les droits d'accès au chatbot AdmiGuide."""

    def setUp(self):
        """Prépare deux utilisateurs et une situation privée."""

        utilisateur = get_user_model()

        self.proprietaire = utilisateur.objects.create_user(
            email="proprietaire@example.com",
            password="MotDePasseTest123!",
            nom_complet="Utilisateur propriétaire",
        )

        self.autre_utilisateur = utilisateur.objects.create_user(
            email="autre@example.com",
            password="MotDePasseTest123!",
            nom_complet="Autre utilisateur",
        )

        self.situation = SituationAdministrative.objects.create(
            utilisateur=self.proprietaire,
            description_initiale="J'ai acheté un terrain au Sénégal.",
        )

        demarche = DemarcheAdministrative.objects.create(
            code="ACQUISITION_MUTATION_TITRE_FONCIER",
            intitule="Acquisition et mutation d'un titre foncier",
            description="Démarche foncière de test.",
        )

        OrientationAdministrative.objects.create(
            situation=self.situation,
            demarche=demarche,
            resume="Orientation foncière de test.",
        )

        self.url = reverse(
            "situation-chat",
            kwargs={"public_id": self.situation.public_id},
        )

        self.donnees = {
            "question": "Que signifie mutation foncière ?",
            "page": "RESULTAT",
        }

    def client_connecte(self, utilisateur):
        """Crée un client authentifié avec un vrai jeton JWT."""

        client = APIClient()
        jeton = AccessToken.for_user(utilisateur)

        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jeton}"
        )

        return client

    @patch("orientations.views.interroger_chatbot")
    def test_proprietaire_autorise(self, appel_ia):
        """Le propriétaire peut utiliser son chatbot."""

        appel_ia.return_value = {
            "reponse": "Explication de la mutation foncière.",
            "sources": [],
        }

        client = self.client_connecte(self.proprietaire)
        reponse = client.post(self.url, self.donnees, format="json")

        self.assertEqual(reponse.status_code, 200)
        appel_ia.assert_called_once()

    @patch("orientations.views.interroger_chatbot")
    def test_autre_utilisateur_refuse(self, appel_ia):
        """Un autre compte ne peut pas consulter la situation."""

        client = self.client_connecte(self.autre_utilisateur)
        reponse = client.post(self.url, self.donnees, format="json")

        self.assertEqual(reponse.status_code, 404)
        appel_ia.assert_not_called()

    @patch("orientations.views.interroger_chatbot")
    def test_visiteur_refuse_sur_situation_privee(self, appel_ia):
        """Un visiteur ne peut pas consulter une situation privée."""

        client = APIClient()
        reponse = client.post(self.url, self.donnees, format="json")

        self.assertEqual(reponse.status_code, 404)
        appel_ia.assert_not_called()

    @patch("orientations.views.interroger_chatbot")
    def test_suivi_reserve_au_proprietaire(self, appel_ia):
        """Le chatbot de suivi reste réservé au propriétaire."""

        appel_ia.return_value = {
            "reponse": "Explication du suivi.",
            "sources": [],
        }

        client = self.client_connecte(self.proprietaire)

        reponse = client.post(
            self.url,
            {
                "question": "Explique-moi mon suivi.",
                "page": "SUIVI",
            },
            format="json",
        )

        self.assertEqual(reponse.status_code, 200)
        appel_ia.assert_called_once()
