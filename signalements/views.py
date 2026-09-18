from django.db import transaction

from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from config.pagination import StandardPagination
from orientations.models import (
    OrientationAdministrative,
    SituationAdministrative,
)

from .models import Signalement
from .serializers import (
    AdminSignalementSerializer,
    AdminSignalementUpdateSerializer,
    SignalementCreateSerializer,
)


class SignalementCreateView(generics.CreateAPIView):
    """Permet à un usager de signaler un problème sur une orientation."""

    serializer_class = SignalementCreateSerializer
    permission_classes = [AllowAny]

    def _get_orientation(self):
        """Retourne l'orientation si la situation est accessible."""
        try:
            situation = SituationAdministrative.objects.get(
                public_id=self.kwargs["public_id"],
            )
        except SituationAdministrative.DoesNotExist:
            raise NotFound("Situation introuvable.")

        # Une situation liée à un compte reste privée.
        if situation.utilisateur_id is not None:
            if (
                not self.request.user.is_authenticated
                or situation.utilisateur_id != self.request.user.id
            ):
                raise NotFound("Situation introuvable.")

        try:
            return situation.orientation
        except OrientationAdministrative.DoesNotExist:
            raise NotFound("Orientation introuvable.")

    def perform_create(self, serializer):
        """Associe le signalement à l'orientation et à son auteur éventuel."""
        utilisateur = (
            self.request.user
            if self.request.user.is_authenticated
            else None
        )

        serializer.save(
            orientation=self._get_orientation(),
            utilisateur=utilisateur,
        )


class AdminSignalementListView(generics.ListAPIView):
    """Liste les signalements pour l'espace administrateur."""

    serializer_class = AdminSignalementSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    filter_backends = [SearchFilter]
    search_fields = [
        "commentaire",
        "orientation__situation__description_initiale",
        "orientation__demarche__intitule",
        "utilisateur__nom_complet",
        "utilisateur__email",
    ]

    def get_queryset(self):
        """Retourne les signalements selon les filtres demandés."""
        queryset = (
            Signalement.objects
            .select_related(
                "orientation",
                "orientation__situation",
                "orientation__demarche",
                "utilisateur",
                "traitement",
                "traitement__administrateur",
            )
            .order_by("-date_creation")
        )

        statut = self.request.query_params.get("statut")

        if statut:
            queryset = queryset.filter(statut=statut)

        type_probleme = self.request.query_params.get("type")

        if type_probleme:
            queryset = queryset.filter(
                type_probleme=type_probleme,
            )

        return queryset


class AdminSignalementDetailView(generics.RetrieveUpdateAPIView):
    """Permet à un administrateur d'examiner un signalement."""

    permission_classes = [IsAdminUser]
    http_method_names = ["get", "patch", "options"]

    queryset = (
        Signalement.objects
        .select_related(
            "orientation",
            "orientation__situation",
            "orientation__demarche",
            "utilisateur",
            "traitement",
            "traitement__administrateur",
        )
    )

    def get_serializer_class(self):
        """Utilise un sérialiseur différent pour la modification."""
        if self.request.method == "PATCH":
            return AdminSignalementUpdateSerializer

        return AdminSignalementSerializer

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """Met à jour puis retourne le signalement complet."""
        signalement = self.get_object()

        serializer = self.get_serializer(
            signalement,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Recharge les relations, notamment le traitement nouvellement créé.
        signalement.refresh_from_db()

        response_serializer = AdminSignalementSerializer(
            signalement,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
