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

    role = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "nom_complet",
            "email",
            "pays_residence",
            "role",
        ]

        # Ces champs ne sont pas modifiables depuis le profil.
        read_only_fields = [
            "id",
            "email",
            "role",
        ]

    def get_role(self, obj):
        """Retourne un rôle simple à utiliser côté frontend."""

        return "admin" if obj.is_staff else "user"


class AdminUserSerializer(serializers.ModelSerializer):
    """Sérialise un compte pour l'espace administrateur."""

    role = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "nom_complet",
            "email",
            "pays_residence",
            "role",
            "is_active",
        ]

        read_only_fields = fields

    def get_role(self, obj):
        """Retourne le rôle affiché dans l'administration."""
        return "admin" if obj.is_staff else "user"


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Sérialise le détail d'un compte pour l'administration."""

    role = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "nom_complet",
            "email",
            "pays_residence",
            "role",
            "is_active",
            "date_joined",
        ]

        # Seul le statut du compte peut être modifié ici.
        read_only_fields = [
            "id",
            "nom_complet",
            "email",
            "pays_residence",
            "role",
            "date_joined",
        ]

    def get_role(self, obj):
        """Retourne le rôle affiché dans l'administration."""
        return "admin" if obj.is_staff else "user"


    
class LogoutSerializer(serializers.Serializer):
    """Valide le refresh token envoyé lors de la déconnexion."""

    # Token nécessaire pour invalider la session de l'utilisateur.
    refresh = serializers.CharField(write_only=True)