from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="http://localhost:4200",
)
class PasswordResetTests(APITestCase):
    """Tests du parcours de réinitialisation du mot de passe."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="awa@gmail.com",
            nom_complet="Awa Ndiaye",
            password="AncienMotDePasse123!",
        )

    def test_password_reset_request_sends_email(self):
        """Un compte existant reçoit un e-mail de réinitialisation."""

        response = self.client.post(
            reverse("password-reset"),
            {
                "email": self.user.email,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        self.assertIn(
            "reinitialiser-mot-de-passe",
            mail.outbox[0].body,
        )

    def test_password_reset_request_hides_unknown_email(self):
        """Une adresse inconnue reçoit la même réponse publique."""

        response = self.client.post(
            reverse("password-reset"),
            {
                "email": "inconnu@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(mail.outbox),
            0,
        )

    def test_password_reset_confirm_changes_password(self):
        """Un token valide permet de définir un nouveau mot de passe."""

        uid = urlsafe_base64_encode(
            force_bytes(self.user.pk)
        )

        token = default_token_generator.make_token(
            self.user
        )

        response = self.client.post(
            reverse(
                "password-reset-confirm",
                kwargs={
                    "uidb64": uid,
                    "token": token,
                },
            ),
            {
                "new_password": "NouveauMotDePasse123!",
                "confirm_password": "NouveauMotDePasse123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "NouveauMotDePasse123!"
            )
        )

    def test_password_reset_confirm_rejects_invalid_token(self):
        """Un token invalide ne permet pas de modifier le mot de passe."""

        uid = urlsafe_base64_encode(
            force_bytes(self.user.pk)
        )

        response = self.client.post(
            reverse(
                "password-reset-confirm",
                kwargs={
                    "uidb64": uid,
                    "token": "token-invalide",
                },
            ),
            {
                "new_password": "NouveauMotDePasse123!",
                "confirm_password": "NouveauMotDePasse123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_password_reset_requires_matching_passwords(self):
        """Les deux mots de passe doivent être identiques."""

        uid = urlsafe_base64_encode(
            force_bytes(self.user.pk)
        )

        token = default_token_generator.make_token(
            self.user
        )

        response = self.client.post(
            reverse(
                "password-reset-confirm",
                kwargs={
                    "uidb64": uid,
                    "token": token,
                },
            ),
            {
                "new_password": "NouveauMotDePasse123!",
                "confirm_password": "AutreMotDePasse123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )