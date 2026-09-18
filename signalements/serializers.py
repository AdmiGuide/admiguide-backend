from rest_framework import serializers

from .models import (
    Signalement,
    TraitementSignalement,
)


class SignalementCreateSerializer(serializers.ModelSerializer):
    """Valide un signalement envoyé depuis une orientation."""

    class Meta:
        model = Signalement
        fields = [
            "id",
            "type_probleme",
            "commentaire",
            "statut",
            "date_creation",
        ]
        read_only_fields = [
            "id",
            "statut",
            "date_creation",
        ]


class TraitementSignalementSerializer(serializers.ModelSerializer):
    """Sérialise le traitement administratif d'un signalement."""

    administrateur_nom = serializers.CharField(
        source="administrateur.nom_complet",
        read_only=True,
    )

    resultat_label = serializers.CharField(
        source="get_resultat_display",
        read_only=True,
    )

    class Meta:
        model = TraitementSignalement
        fields = [
            "id",
            "administrateur_nom",
            "commentaire_administrateur",
            "resultat",
            "resultat_label",
            "suite_a_donner",
            "date_traitement",
        ]


class AdminSignalementSerializer(serializers.ModelSerializer):
    """Sérialise un signalement pour l'espace administrateur."""

    type_probleme_label = serializers.CharField(
        source="get_type_probleme_display",
        read_only=True,
    )

    statut_label = serializers.CharField(
        source="get_statut_display",
        read_only=True,
    )

    orientation_public_id = serializers.UUIDField(
        source="orientation.situation.public_id",
        read_only=True,
    )

    demarche = serializers.SerializerMethodField()

    description_situation = serializers.CharField(
        source="orientation.situation.description_initiale",
        read_only=True,
    )

    utilisateur_nom = serializers.SerializerMethodField()
    utilisateur_email = serializers.SerializerMethodField()

    traitement = TraitementSignalementSerializer(
        read_only=True,
    )

    class Meta:
        model = Signalement
        fields = [
            "id",
            "orientation_public_id",
            "demarche",
            "description_situation",
            "utilisateur_nom",
            "utilisateur_email",
            "type_probleme",
            "type_probleme_label",
            "commentaire",
            "statut",
            "statut_label",
            "date_creation",
            "date_mise_a_jour",
            "traitement",
        ]

    def get_demarche(self, obj):
        """Retourne le nom de la démarche concernée."""

        if not obj.orientation.demarche:
            return "Démarche non identifiée"

        return obj.orientation.demarche.intitule

    def get_utilisateur_nom(self, obj):
        """Retourne le nom de l'auteur ou Visiteur."""

        if not obj.utilisateur:
            return "Visiteur"

        return obj.utilisateur.nom_complet

    def get_utilisateur_email(self, obj):
        """Retourne l'e-mail lorsqu'un compte est associé."""

        if not obj.utilisateur:
            return None

        return obj.utilisateur.email


class AdminSignalementUpdateSerializer(serializers.ModelSerializer):
    """Permet à l'administrateur de modifier le statut."""

    class Meta:
        model = Signalement
        fields = [
            "statut",
        ]