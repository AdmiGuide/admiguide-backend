from django.conf import settings
from django.db import models

from orientations.models import OrientationAdministrative


class TypeProblemeSignalement(models.TextChoices):
    """Définit le type de problème signalé par l'usager."""

    INFORMATION_INCORRECTE = (
        "INFORMATION_INCORRECTE",
        "Information incorrecte",
    )
    INFORMATION_INCOMPLETE = (
        "INFORMATION_INCOMPLETE",
        "Information incomplète",
    )
    INFORMATION_OBSOLETE = (
        "INFORMATION_OBSOLETE",
        "Information obsolète",
    )
    AUTRE = "AUTRE", "Autre"


class StatutSignalement(models.TextChoices):
    """Définit l'état d'avancement d'un signalement."""

    NOUVEAU = "NOUVEAU", "Nouveau"
    EN_COURS = "EN_COURS", "En cours"
    TRAITE = "TRAITE", "Traité"


class ResultatTraitement(models.TextChoices):
    """Définit le résultat final du traitement administratif."""

    RESOLU = "RESOLU", "Résolu"
    NON_RESOLU = "NON_RESOLU", "Non résolu"
    REJETE = "REJETE", "Rejeté"


class Signalement(models.Model):
    """Représente un problème signalé sur une orientation."""

    orientation = models.ForeignKey(
        OrientationAdministrative,
        on_delete=models.CASCADE,
        related_name="signalements",
    )

    # Le signalement peut être envoyé par un visiteur sans compte.
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signalements",
    )

    type_probleme = models.CharField(
        max_length=30,
        choices=TypeProblemeSignalement.choices,
        verbose_name="type de problème",
    )

    commentaire = models.TextField(
        max_length=1000,
        verbose_name="commentaire",
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutSignalement.choices,
        default=StatutSignalement.NOUVEAU,
        verbose_name="statut",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création",
    )

    date_mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour",
    )

    def __str__(self):
        """Retourne une représentation courte du signalement."""
        return f"Signalement {self.id} - {self.get_statut_display()}"


class TraitementSignalement(models.Model):
    """Enregistre le traitement réalisé par un administrateur."""

    signalement = models.OneToOneField(
        Signalement,
        on_delete=models.CASCADE,
        related_name="traitement",
    )

    administrateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="traitements_signalements",
    )

    commentaire_administrateur = models.TextField(
        max_length=1500,
        verbose_name="commentaire administrateur",
    )

    resultat = models.CharField(
        max_length=20,
        choices=ResultatTraitement.choices,
        verbose_name="résultat",
    )

    suite_a_donner = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name="suite à donner",
    )

    date_traitement = models.DateTimeField(
        auto_now=True,
        verbose_name="date de traitement",
    )

    def __str__(self):
        """Retourne le signalement traité."""
        return f"Traitement du signalement {self.signalement_id}"
