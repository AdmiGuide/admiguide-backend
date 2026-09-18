from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from orientations.models import (
    OrientationAdministrative,
    SituationAdministrative,
)
from referentiel.models import DemarcheAdministrative

from .models import (
    Signalement,
    StatutSignalement,
)


User = get_user_model()


class SignalementAPITest(APITestCase):
    """Teste les principales actions liées aux signalements."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            password="Test1234!",
            nom_complet="Utilisateur Test",
            pays_residence="Sénégal",
        )

        self.other_user = User.objects.create_user(
            email="other@test.com",
            password="Test1234!",
            nom_complet="Autre Utilisateur",
            pays_residence="Sénégal",
        )

        self.admin = User.objects.create_superuser(
            email="admin@test.com",
            password="Test1234!",
            nom_complet="Admin Test",
            pays_residence="Sénégal",
        )

        self.demarche = DemarcheAdministrative.objects.create(
            code="TEST_SIGNALEMENT",
            intitule="Démarche signalée",
            description="Démarche utilisée pour les tests.",
        )

        self.situation = SituationAdministrative.objects.create(
            utilisateur=self.user,
            description_initiale="Situation privée à signaler.",
            pays_application="SN",
        )

        self.orientation = OrientationAdministrative.objects.create(
            situation=self.situation,
            demarche=self.demarche,
            resume="Orientation de test.",
        )

    def test_utilisateur_peut_creer_signalement(self):
        """Un utilisateur peut signaler sa propre orientation."""

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse(
                "signalement-create",
                kwargs={"public_id": self.situation.public_id},
            ),
            {
                "type_probleme": "INFORMATION_INCORRECTE",
                "commentaire": "Le coût indiqué semble incorrect.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        signalement = Signalement.objects.get()

        self.assertEqual(
            signalement.utilisateur,
            self.user,
        )

        self.assertEqual(
            signalement.orientation,
            self.orientation,
        )

        self.assertEqual(
            signalement.statut,
            StatutSignalement.NOUVEAU,
        )

    def test_visiteur_peut_signaler_orientation_anonyme(self):
        """Un visiteur peut signaler une orientation anonyme."""

        situation = SituationAdministrative.objects.create(
            description_initiale="Situation anonyme à signaler.",
            pays_application="SN",
        )

        orientation = OrientationAdministrative.objects.create(
            situation=situation,
            demarche=self.demarche,
            resume="Orientation anonyme.",
        )

        response = self.client.post(
            reverse(
                "signalement-create",
                kwargs={"public_id": situation.public_id},
            ),
            {
                "type_probleme": "INFORMATION_INCOMPLETE",
                "commentaire": "Une pièce semble manquer.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        signalement = Signalement.objects.get(
            orientation=orientation,
        )

        self.assertIsNone(signalement.utilisateur)

        self.assertEqual(
            signalement.statut,
            StatutSignalement.NOUVEAU,
        )

    def test_autre_utilisateur_ne_peut_pas_signaler_situation_privee(self):
        """Un utilisateur ne peut pas signaler la situation privée d'un autre."""

        self.client.force_authenticate(
            user=self.other_user,
        )

        response = self.client.post(
            reverse(
                "signalement-create",
                kwargs={"public_id": self.situation.public_id},
            ),
            {
                "type_probleme": "AUTRE",
                "commentaire": "Test accès interdit.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_peut_marquer_signalement_en_cours(self):
        """Un administrateur peut prendre en charge un signalement."""

        signalement = Signalement.objects.create(
            orientation=self.orientation,
            utilisateur=self.user,
            type_probleme="INFORMATION_OBSOLETE",
            commentaire="Cette information semble ancienne.",
        )

        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.patch(
            reverse(
                "admin-signalement-detail",
                kwargs={"pk": signalement.id},
            ),
            {
                "statut": "EN_COURS",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["statut"],
            "EN_COURS",
        )

        signalement.refresh_from_db()

        self.assertEqual(
            signalement.statut,
            StatutSignalement.EN_COURS,
        )

    def test_admin_peut_marquer_signalement_comme_traite(self):
        """Un administrateur peut clôturer un signalement."""

        signalement = Signalement.objects.create(
            orientation=self.orientation,
            utilisateur=self.user,
            type_probleme="INFORMATION_INCORRECTE",
            commentaire="Une information doit être vérifiée.",
            statut=StatutSignalement.EN_COURS,
        )

        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.patch(
            reverse(
                "admin-signalement-detail",
                kwargs={"pk": signalement.id},
            ),
            {
                "statut": "TRAITE",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["statut"],
            "TRAITE",
        )

        signalement.refresh_from_db()

        self.assertEqual(
            signalement.statut,
            StatutSignalement.TRAITE,
        )

    def test_utilisateur_standard_ne_peut_pas_lister_signalements(self):
        """La liste des signalements est réservée aux administrateurs."""

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.get(
            reverse("admin-signalement-list"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )