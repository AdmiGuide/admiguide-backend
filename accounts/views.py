from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import RegisterSerializer, ProfileSerializer, LogoutSerializer


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