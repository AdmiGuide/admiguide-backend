from django.db import models


class Administration(models.Model):
    """
    Représente une administration ou institution compétente
    pour une ou plusieurs démarches administratives.
    """

    nom = models.CharField(
        max_length=200,
        verbose_name="nom de l'administration",
    )

    sigle = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="sigle",
    )

    site_web = models.URLField(
        blank=True,
        verbose_name="site web",
    )

    def __str__(self):
        """Retourne le nom de l'administration."""
        return self.nom



class ServiceAdministratif(models.Model):
    """
    Représente un service administratif rattaché à une administration.

    Il permet d'indiquer à l'usager quel service est compétent
    pour effectuer une démarche.
    """

    administration = models.ForeignKey(
        Administration,
        on_delete=models.CASCADE,
        related_name="services",
    )

    nom = models.CharField(
        max_length=200,
        verbose_name="nom du service",
    )

    adresse = models.TextField(
        blank=True,
        verbose_name="adresse",
    )

    contact = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="contact",
    )

    def __str__(self):
        """Retourne le nom du service et de son administration."""
        return f"{self.nom} - {self.administration.nom}"




class DemarcheAdministrative(models.Model):
    """
    Représente une démarche administrative pouvant être
    recommandée à l'usager à la suite de l'analyse de sa situation.
    """

    intitule = models.CharField(
        max_length=255,
        verbose_name="intitulé",
    )

    description = models.TextField(
        verbose_name="description",
    )

    cout_indicatif = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="coût indicatif",
    )

    delai_indicatif = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="délai indicatif",
    )

    # Une démarche peut être prise en charge par plusieurs services.
    services = models.ManyToManyField(
        ServiceAdministratif,
        related_name="demarches",
        blank=True,
    )

    date_mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour",
    )

    def __str__(self):
        """Retourne l'intitulé de la démarche."""
        return self.intitule



class EtapeDemarche(models.Model):
    """
    Représente une étape à suivre dans une démarche administrative.
    """

    demarche = models.ForeignKey(
        DemarcheAdministrative,
        on_delete=models.CASCADE,
        related_name="etapes",
    )

    ordre = models.PositiveIntegerField(
        verbose_name="ordre",
    )

    description = models.TextField(
        verbose_name="description",
    )

    class Meta:
        # Les étapes sont récupérées automatiquement dans leur ordre logique.
        ordering = ["ordre"]

    def __str__(self):
        """Retourne le numéro et la démarche de l'étape."""
        return f"Étape {self.ordre} - {self.demarche.intitule}"


class PieceRequise(models.Model):
    """
    Représente une pièce ou information nécessaire
    pour réaliser une démarche administrative.
    """

    demarche = models.ForeignKey(
        DemarcheAdministrative,
        on_delete=models.CASCADE,
        related_name="pieces_requises",
    )

    libelle = models.CharField(
        max_length=255,
        verbose_name="libellé",
    )

    obligatoire = models.BooleanField(
        default=True,
        verbose_name="obligatoire",
    )

    def __str__(self):
        """Retourne le nom de la pièce requise."""
        return self.libelle


    
class TypeSource(models.TextChoices):
    """Définit les types de sources administratives gérées par AdmiGuide."""

    API = "API", "API"
    PAGE_WEB = "PAGE_WEB", "Page web"
    DOCUMENT = "DOCUMENT", "Document"


class StatutSource(models.TextChoices):
    """Définit l'état de disponibilité d'une source administrative."""

    DISPONIBLE = "DISPONIBLE", "Disponible"
    INDISPONIBLE = "INDISPONIBLE", "Indisponible"
    A_VERIFIER = "A_VERIFIER", "À vérifier"



class SourceAdministrative(models.Model):
    """
    Représente une source officielle utilisée par AdmiGuide
    pour produire ou justifier une orientation administrative.
    """

    titre = models.CharField(
        max_length=255,
        verbose_name="titre",
    )

    url = models.URLField(
        verbose_name="URL de la source",
    )

    type = models.CharField(
        max_length=20,
        choices=TypeSource.choices,
        verbose_name="type de source",
    )

    statut = models.CharField(
    max_length=20,
    choices=StatutSource.choices,
    default=StatutSource.DISPONIBLE,
    verbose_name="statut",
    )

    date_consultation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="date de dernière consultation",
    )

    date_mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour",
    )
    
    # Relie une source aux démarches qu'elle permet de documenter.
    demarches = models.ManyToManyField(
        DemarcheAdministrative,
        related_name="sources",
        blank=True,
    )

    def __str__(self):
        """Retourne le titre de la source."""
        return self.titre