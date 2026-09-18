from django.urls import path

from .views import AdminSourceListView


urlpatterns = [
    # Liste des sources pour l'administration.
    path(
        "admin/sources/",
        AdminSourceListView.as_view(),
        name="admin-source-list",
    ),
]