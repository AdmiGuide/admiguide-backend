from django.shortcuts import render

from rest_framework import generics, status, serializers
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    AdminUserSerializer,
    AdminUserDetailSerializer,
    LogoutSerializer,
    ProfileSerializer,
    RegisterSerializer,
)
from config.pagination import StandardPagination
from rest_framework.filters import SearchFilter

class RegisterView(generics.CreateAPIView):
    """Permet à un visiteur de créer un compte utilisateur."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    # L'inscription doit être accessible sans être connecté.
    permission_classes = [AllowAny]


class LogoutView(generics.GenericAPIView):
    """Déconnecte l'utilisateur en invalidant son refresh token."""

    serializer_class = LogoutSerializer

    # Le refresh token suffit pour effectuer la déconnexion.
    permission_classes = [AllowAny]

    def post(self, request):
        """Valide puis ajoute le refresh token reçu à la blacklist."""

        # Vérifie que la requête contient bien un refresh token.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]

        try:
            # Invalide le refresh token afin qu'il ne puisse plus être réutilisé.
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"detail": "Déconnexion réussie."},
                status=status.HTTP_200_OK,
            )

        except TokenError:
            return Response(
                {"detail": "Refresh token invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Permet à l'utilisateur connecté de consulter ou modifier son profil."""

    serializer_class = ProfileSerializer

    # Seul un utilisateur authentifié peut accéder à son profil.
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Retourne uniquement l'utilisateur actuellement connecté."""
        return self.request.user



class AdminUserListView(generics.ListAPIView):
    """Permet à un administrateur de consulter les comptes."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    # Recherche par nom ou adresse e-mail.
    filter_backends = [SearchFilter]
    search_fields = ["nom_complet", "email"]

    def get_queryset(self):
        """Retourne les comptes selon le filtre de statut."""

        queryset = User.objects.all().order_by("-date_joined")

        status_filter = self.request.query_params.get("status")

        if status_filter == "actif":
            queryset = queryset.filter(is_active=True)

        elif status_filter == "suspendu":
            queryset = queryset.filter(is_active=False)

        return queryset



class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """Permet à l'administrateur de consulter et gérer un compte."""

    queryset = User.objects.all()
    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        """Empêche l'administrateur de suspendre son propre compte."""

        user = self.get_object()

        if (
            user.id == self.request.user.id
            and serializer.validated_data.get("is_active") is False
        ):
            raise serializers.ValidationError(
                {
                    "is_active":
                        "Vous ne pouvez pas suspendre votre propre compte."
                }
            )

        serializer.save()