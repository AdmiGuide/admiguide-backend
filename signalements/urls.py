from django.urls import path

from .views import (
    AdminSignalementDetailView,
    AdminSignalementListView,
    SignalementCreateView,
)


urlpatterns = [
    # Création d'un signalement depuis une orientation.
    path(
        "situations/<uuid:public_id>/",
        SignalementCreateView.as_view(),
        name="signalement-create",
    ),

    # Liste réservée à l'administration.
    path(
        "admin/",
        AdminSignalementListView.as_view(),
        name="admin-signalement-list",
    ),

    # Consultation et traitement d'un signalement.
    path(
        "admin/<int:pk>/",
        AdminSignalementDetailView.as_view(),
        name="admin-signalement-detail",
    ),
]
