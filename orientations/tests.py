from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from referentiel.models import DemarcheAdministrative, EtapeDemarche

from .models import (
    OrientationAdministrative,
    SituationAdministrative,
    SuiviEtape,
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
            pays_residence="Sénégal",
        )

        self.autre_user = User.objects.create_user(
            email="autre@test.com",
            password="Test1234!",
            nom_complet="Autre Utilisateur",
            pays_residence="Sénégal",
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
            pays_application="SN",
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["terminee"])

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

        self.assertTrue(suivi.terminee)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["terminee"])
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.data["progression"],
            {
                "terminees": 2,
                "total": 2,
                "pourcentage": 100,
            },
        )

    def test_interdire_modification_autre_utilisateur(self):
        """Un utilisateur ne peut pas modifier la feuille de route d'un autre."""

        self.client.force_authenticate(user=self.autre_user)

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
