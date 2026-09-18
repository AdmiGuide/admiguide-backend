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