from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    AdminUserListView,
    LogoutView,
    ProfileView,
    RegisterView,
    AdminUserDetailView
)


urlpatterns = [
    # Création d'un nouveau compte utilisateur.
    path("register/", RegisterView.as_view(), name="register"),

    # Authentifie l'utilisateur et retourne un access token et un refresh token.
    path("login/", TokenObtainPairView.as_view(), name="login"),

    # Génère un nouvel access token à partir d'un refresh token valide.
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Déconnexion par invalidation du refresh token.
    path("logout/", LogoutView.as_view(), name="logout"),

    # Consultation et modification du profil de l'utilisateur connecté.
    path("profile/", ProfileView.as_view(), name="profile"),

    # Liste des comptes réservée à l'administration.
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),

    # Consultation et gestion d'un compte par l'administrateur.
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail",),

]