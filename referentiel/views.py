from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAdminUser

from config.pagination import StandardPagination

from .models import SourceAdministrative
from .serializers import AdminSourceSerializer


class AdminSourceListView(generics.ListAPIView):
    """Liste les sources officielles pour l'espace administrateur."""

    serializer_class = AdminSourceSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    # Recherche par titre ou URL.
    filter_backends = [SearchFilter]
    search_fields = ["titre", "url"]

    def get_queryset(self):
        queryset = SourceAdministrative.objects.all().order_by(
            "-date_mise_a_jour"
        )

        # Filtre par statut.
        statut = self.request.query_params.get("statut")

        if statut:
            queryset = queryset.filter(statut=statut)

        # Filtre par type de source.
        type_source = self.request.query_params.get("type")

        if type_source:
            queryset = queryset.filter(type=type_source)

        return queryset