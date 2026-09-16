from django.urls import path

from .views import (
    QuestionListView,
    ReponseComplementaireView,
    SituationCreateView,
    SituationHistoryView,
    SituationResultView,
    SituationUpdateView,
    SuiviEtapeUpdateView,
)

urlpatterns = [
    # Enregistre la situation décrite par l'usager.
    path(
        "situations/", SituationCreateView.as_view(),
        name="situation-create",),

    # Retourne l'orientation correspondant à une situation.
    path(
        "situations/<uuid:public_id>/resultat/",
        SituationResultView.as_view(),
        name="situation-result",
    ),

    # Retourne l'historique de l'utilisateur actuellement connecté.
    path(
        "historique/", SituationHistoryView.as_view(),
        name="situation-history",
    ),

    # Retourne les questions complémentaires d'une situation.
    path(
        "situations/<uuid:public_id>/questions/",
        QuestionListView.as_view(),
        name="situation-questions",
    ),

    # Enregistre les réponses aux questions complémentaires.
    path(
        "situations/<uuid:public_id>/reponses/",
        ReponseComplementaireView.as_view(),
        name="situation-reponses",
    ),

    # Permet de modifier la description initiale d'une situation.
    path(
        "situations/<uuid:public_id>/",
        SituationUpdateView.as_view(),
        name="situation-update",
    ),

    # Permet de mettre à jour une étape de la feuille de route.
    path(
        "situations/<uuid:public_id>/etapes/<int:etape_id>/",
        SuiviEtapeUpdateView.as_view(),
        name="situation-etape-update",
    ),
]