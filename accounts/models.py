from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Gestionnaire personnalisé des utilisateurs AdmiGuide.

    Il permet de créer les utilisateurs à partir de leur adresse email,
    utilisée comme identifiant de connexion à la place du username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Crée et enregistre un utilisateur standard."""

        if not email:
            raise ValueError("L'adresse email est obligatoire.")

        if not password:
            raise ValueError("Le mot de passe est obligatoire.")

        # Normalise notamment le domaine de l'adresse email.
        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields,
        )

        # Hash le mot de passe avant son stockage.
        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Crée un administrateur disposant des droits Django."""

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Un superutilisateur doit avoir is_staff=True."
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Un superutilisateur doit avoir is_superuser=True."
            )

        return self.create_user(
            email,
            password,
            **extra_fields,
        )


class User(AbstractUser):
    """
    Représente un utilisateur d'AdmiGuide.

    L'adresse email est utilisée comme identifiant de connexion.
    Les mécanismes natifs de Django assurent la gestion sécurisée
    des mots de passe et des permissions.
    """

    # Le username Django n'est pas utilisé dans AdmiGuide.
    username = None

    # Ces deux champs Django sont remplacés par nom_complet.
    first_name = None
    last_name = None

    email = models.EmailField(
        unique=True,
        verbose_name="adresse email",
    )

    nom_complet = models.CharField(
        max_length=200,
        verbose_name="nom complet",
    )

    pays_residence = models.CharField(
        max_length=100,
        verbose_name="pays de résidence",
    )

    # L'email devient l'identifiant utilisé pour la connexion.
    USERNAME_FIELD = "email"

    # Champ supplémentaire demandé par createsuperuser.
    REQUIRED_FIELDS = [
        "nom_complet",
        "pays_residence",
        ]

    # Utilise notre gestionnaire personnalisé.
    objects = UserManager()

    def __str__(self):
        """Retourne une représentation lisible de l'utilisateur."""
        return f"{self.nom_complet} ({self.email})"