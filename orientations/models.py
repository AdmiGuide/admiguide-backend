from django.db import models
from django.conf import settings
import uuid
from referentiel.models import DemarcheAdministrative, EtapeDemarche

class SituationAdministrative(models.Model):
    """
    Représente une situation administrative décrite par un usager.

    Une situation peut appartenir à un utilisateur connecté ou être
    créée anonymement lorsqu'un visiteur utilise le service sans compte.
    """

    # Identifiant public unique utilisé pour accéder à une situation sans exposer son id numérique.
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="identifiant public",
    )

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="situations",
    )

        # Description de la situation fournie par l'usager.
    description_initiale = models.TextField(
        max_length=1500,
        verbose_name="description initiale",
    )

    # Pays dans lequel la démarche doit être effectuée.
    # Exemples : SN, FR ou ETRANGER.
    pays_application = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="pays d'application",
    )

    # Pays de résidence renseigné pendant l'étape de précisions.
    pays_residence = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="pays de résidence",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création",
    )

    def __str__(self):
        """Retourne une représentation courte de la situation."""
        return f"Situation {self.id} - {self.date_creation:%d/%m/%Y}"



class TypeQuestion(models.TextChoices):
    """Définit la manière dont l'utilisateur doit répondre à une question."""

    TEXTE = "TEXTE", "Texte"
    CHOIX_UNIQUE = "CHOIX_UNIQUE", "Choix unique"


class QuestionComplementaire(models.Model):
    """
    Représente une question posée pour préciser une situation administrative.

    Une situation peut nécessiter plusieurs questions complémentaires
    avant que le système puisse produire une orientation suffisamment précise.
    """

    situation = models.ForeignKey(
        SituationAdministrative,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    texte = models.TextField(
        verbose_name="texte de la question",
    )

    # Indique au frontend quel composant utiliser pour la réponse.
    type_question = models.CharField(
        max_length=20,
        choices=TypeQuestion.choices,
        default=TypeQuestion.TEXTE,
        verbose_name="type de question",
    )

    # Contient les choix proposés lorsqu'il s'agit d'une question à choix unique.
    options = models.JSONField(
        default=list,
        blank=True,
        verbose_name="options de réponse",
    )

    ordre = models.PositiveIntegerField(
        default=1,
        verbose_name="ordre d'affichage",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création",
    )

    def __str__(self):
        """Retourne une représentation lisible de la question."""
        return f"Question {self.id} - Situation {self.situation_id}"



class ReponseComplementaire(models.Model):
    """
    Représente la réponse donnée par l'usager
    à une question complémentaire.
    """

    question = models.OneToOneField(
        QuestionComplementaire,
        on_delete=models.CASCADE,
        related_name="reponse",
    )

    contenu = models.TextField(
        verbose_name="contenu de la réponse",
    )

    date_reponse = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de réponse",
    )

    def __str__(self):
        """Retourne la question à laquelle cette réponse appartient."""
        return f"Réponse à la question {self.question_id}"



class OrientationAdministrative(models.Model):
    """
    Représente l'orientation produite à partir
    d'une situation administrative analysée.
    """

    situation = models.OneToOneField(
        SituationAdministrative,
        on_delete=models.CASCADE,
        related_name="orientation",
    )

    resume = models.TextField(
        verbose_name="résumé de l'orientation",
    )

    # Relie l'orientation à la démarche administrative recommandée.
    demarche = models.ForeignKey(
        DemarcheAdministrative,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orientations",
    )

    avertissement = models.TextField(
        blank=True,
        verbose_name="avertissement",
    )

    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de génération",
    )

    def __str__(self):
        """Retourne la situation associée à l'orientation."""
        return f"Orientation de la situation {self.situation_id}"



class SuiviEtape(models.Model):
    """Enregistre l'avancement d'une étape pour une orientation."""

    orientation = models.ForeignKey(
        OrientationAdministrative,
        on_delete=models.CASCADE,
        related_name="suivis_etapes",
    )

    etape = models.ForeignKey(
        EtapeDemarche,
        on_delete=models.CASCADE,
        related_name="suivis",
    )

    terminee = models.BooleanField(
        default=False,
        verbose_name="étape terminée",
    )

    date_mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["orientation", "etape"],
                name="unique_suivi_etape_orientation",
            )
        ]

    def __str__(self):
        """Retourne l'étape suivie et son état."""
        etat = "terminée" if self.terminee else "à faire"
        return f"{self.etape} - {etat}"