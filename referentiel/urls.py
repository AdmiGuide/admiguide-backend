from django.urls import path

from .views import AdminSourceListView, AdminSourceControlView


urlpatterns = [
    # Liste des sources pour l'administration.
    path(
        "admin/sources/",
        AdminSourceListView.as_view(),
        name="admin-source-list",
    ),

    # Contrôle manuel d'une source.
    path(
        "admin/sources/<int:pk>/control/",
        AdminSourceControlView.as_view(),
        name="admin-source-control",
    ),
]