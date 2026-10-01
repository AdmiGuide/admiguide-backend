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



class Signalement(models.Model):
    """Représente un problème signalé sur une orientation."""

    orientation = models.ForeignKey(
        OrientationAdministrative,
        on_delete=models.CASCADE,
        related_name="signalements",
    )

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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


