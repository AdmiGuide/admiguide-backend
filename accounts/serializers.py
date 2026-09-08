from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Valide les données reçues lors de la création d'un compte
    et crée l'utilisateur de manière sécurisée.
    """

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    class Meta:
        model = User

        fields = [
            "id",
            "nom_complet",
            "email",
            "pays_residence",
            "password",
        ]

        read_only_fields = ["id"]

    def create(self, validated_data):
        """
        Utilise create_user afin que le mot de passe soit hashé
        avant son enregistrement dans la base.
        """

        return User.objects.create_user(
            **validated_data
        )



class ProfileSerializer(serializers.ModelSerializer):
    """Sérialise les informations du profil de l'utilisateur connecté."""

    class Meta:
        model = User
        fields = [
            "id",
            "nom_complet",
            "email",
            "pays_residence",
        ]

        # L'identifiant et l'email ne peuvent pas être modifiés directement depuis le profil
        read_only_fields = ["id", "email"]



class LogoutSerializer(serializers.Serializer):
    """Valide le refresh token envoyé lors de la déconnexion."""

    # Token nécessaire pour invalider la session de l'utilisateur.
    refresh = serializers.CharField(write_only=True)