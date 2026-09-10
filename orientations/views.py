from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound

from .models import (
    QuestionComplementaire,
    ReponseComplementaire,
    SituationAdministrative,
    TypeQuestion,
)
from .serializers import (
    QuestionComplementaireSerializer,
    ReponsesComplementairesSerializer,
    SituationCreateSerializer,
    SituationHistorySerializer,
    SituationResultSerializer,
    SituationUpdateSerializer,
)

# Permet d'enregistrer plusieurs réponses dans une seule transaction.
from django.db import transaction

class SituationCreateView(generics.CreateAPIView):
    """
    Permet à un visiteur ou à un utilisateur connecté
    de décrire une situation administrative.
    """

    queryset = SituationAdministrative.objects.all()
    serializer_class = SituationCreateSerializer

    # Le parcours d'orientation est accessible sans compte.
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        """
        Associe automatiquement la situation à l'utilisateur
        lorsqu'il est authentifié.
        """

        if self.request.user.is_authenticated:
            serializer.save(utilisateur=self.request.user)
        else:
            serializer.save()



class SituationResultView(generics.RetrieveAPIView):
    """
    Retourne le résultat complet associé à une situation administrative.
    """

    serializer_class = SituationResultSerializer

    # Le résultat doit aussi pouvoir être consulté par un visiteur.
    permission_classes = [AllowAny]

    # L'UUID public est utilisé dans l'URL à la place de l'id numérique.
    lookup_field = "public_id"

    def get_queryset(self):
        """
        Charge les relations nécessaires au résultat
        en limitant le nombre de requêtes SQL.
        """

        return (
            SituationAdministrative.objects
            .select_related(
                "orientation",
                "orientation__demarche",
            )
            .prefetch_related(
                "orientation__demarche__etapes",
                "orientation__demarche__pieces_requises",
                "orientation__demarche__services__administration",
                "orientation__demarche__sources",
            )
        )

    def get_object(self):
        """Retourne uniquement une situation accessible au demandeur."""

        return get_accessible_situation(
            self.request,
            self.kwargs["public_id"],
        )


class SituationUpdateView(generics.UpdateAPIView):
    """Permet de modifier la description initiale d'une situation."""

    queryset = SituationAdministrative.objects.all()
    serializer_class = SituationUpdateSerializer
    permission_classes = [AllowAny]

    # Seule la méthode PATCH est nécessaire pour cette fonctionnalité.
    http_method_names = ["patch", "options"]

    # L'UUID public est utilisé à la place de l'id numérique.
    lookup_field = "public_id"

    def get_object(self):
        """Retourne uniquement une situation que le demandeur peut modifier."""

        return get_accessible_situation(
            self.request,
            self.kwargs["public_id"],
        )



class SituationHistoryView(generics.ListAPIView):
    """
    Retourne uniquement les situations appartenant
    à l'utilisateur actuellement connecté.
    """

    serializer_class = SituationHistorySerializer

    # L'historique est réservé aux utilisateurs authentifiés.
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Récupère les situations de l'utilisateur
        de la plus récente à la plus ancienne.
        """

        return (
            SituationAdministrative.objects
            .filter(utilisateur=self.request.user)
            .select_related(
                "utilisateur",
                "orientation",
                "orientation__demarche",
            )
            .order_by("-date_creation")
        )



class QuestionListView(generics.ListAPIView):
    """Retourne les questions complémentaires d'une situation."""

    serializer_class = QuestionComplementaireSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Retourne les questions uniquement si la situation est accessible."""

        # Vérifie d'abord que l'utilisateur peut accéder à cette situation.
        situation = get_accessible_situation(
            self.request,
            self.kwargs["public_id"],
        )

        # Retourne les questions liées à cette situation dans le bon ordre.
        return QuestionComplementaire.objects.filter(
            situation=situation
        ).order_by("ordre")


class ReponseComplementaireView(generics.GenericAPIView):
    """
    Enregistre les réponses complémentaires
    fournies pour une situation.
    """

    serializer_class = ReponsesComplementairesSerializer
    permission_classes = [AllowAny]

    def post(self, request, public_id):
        """Valide toutes les réponses avant de les enregistrer."""

        # Vérifie que le demandeur peut accéder à cette situation.
        situation = get_accessible_situation(
            request,
            public_id,
        )

        # Valide la structure générale du JSON reçu.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reponses_a_enregistrer = []

        # Vérifie d'abord toutes les réponses sans modifier la base.
        for donnee in serializer.validated_data["reponses"]:

            try:
                # Vérifie que la question appartient bien à la situation.
                question = QuestionComplementaire.objects.get(
                    id=donnee["question_id"],
                    situation=situation,
                )
            except QuestionComplementaire.DoesNotExist:
                return Response(
                    {
                        "detail": (
                            f"La question {donnee['question_id']} "
                            "n'appartient pas à cette situation."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            contenu = donnee["contenu"]

            # Vérifie les réponses aux questions à choix unique.
            if (
                question.type_question == TypeQuestion.CHOIX_UNIQUE
                and contenu not in question.options
            ):
                return Response(
                    {
                        "detail": (
                            f"Réponse invalide pour la question "
                            f"{question.id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Prépare la réponse sans encore l'enregistrer.
            reponses_a_enregistrer.append(
                (question, contenu)
            )

        reponses_enregistrees = []

        # Toutes les réponses sont valides :
        # elles sont maintenant enregistrées ensemble.
        with transaction.atomic():

            for question, contenu in reponses_a_enregistrer:

                reponse, _ = ReponseComplementaire.objects.update_or_create(
                    question=question,
                    defaults={"contenu": contenu},
                )

                reponses_enregistrees.append(
                    {
                        "question_id": question.id,
                        "contenu": reponse.contenu,
                    }
                )

        return Response(
            {
                "detail": "Réponses enregistrées.",
                "reponses": reponses_enregistrees,
            },
            status=status.HTTP_200_OK,
        )



def get_accessible_situation(request, public_id):
    """
    Retourne une situation si le demandeur est autorisé à y accéder.

    Une situation anonyme est accessible avec son UUID public.
    Une situation liée à un compte est réservée à son propriétaire.
    """

    try:
        situation = SituationAdministrative.objects.get(
            public_id=public_id
        )
    except SituationAdministrative.DoesNotExist:
        raise NotFound("Situation introuvable.")

    # Une situation liée à un compte est privée.
    if situation.utilisateur_id is not None:
        if (
            not request.user.is_authenticated
            or situation.utilisateur_id != request.user.id
        ):
            # On renvoie 404 pour ne pas révéler l'existence de la situation.
            raise NotFound("Situation introuvable.")

    return situation