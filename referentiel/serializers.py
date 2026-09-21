from django.utils import timezone
from rest_framework import serializers
from .models import SourceAdministrative


class AdminSourceSerializer(serializers.ModelSerializer):
    """Sérialise une source officielle pour l'espace administrateur."""

    type_label = serializers.CharField(
        source="get_type_display",
        read_only=True,
    )

    statut_label = serializers.CharField(
        source="get_statut_display",
        read_only=True,
    )

    class Meta:
        model = SourceAdministrative

        fields = [
            "id",
            "titre",
            "url",
            "type",
            "type_label",
            "statut",
            "statut_label",
            "date_consultation",
            "date_mise_a_jour",
        ]

        read_only_fields = [
            "id",
            "date_mise_a_jour",
        ]



class AdminSourceControlSerializer(serializers.ModelSerializer):
    """Enregistre le contrôle manuel d'une source."""

    statut_label = serializers.CharField(
        source="get_statut_display",
        read_only=True,
    )

    class Meta:
        model = SourceAdministrative

        fields = [
            "id",
            "titre",
            "statut",
            "statut_label",
            "date_consultation",
        ]

        read_only_fields = [
            "id",
            "titre",
            "statut_label",
            "date_consultation",
        ]

    def update(self, instance, validated_data):
        # Met à jour le statut choisi par l'administrateur.
        instance.statut = validated_data["statut"]

        # Enregistre la date du contrôle.
        instance.date_consultation = timezone.now()

        instance.save(
            update_fields=[
                "statut",
                "date_consultation",
                "date_mise_a_jour",
            ]
        )

        return instance