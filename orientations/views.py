from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound, APIException

from .models import (
    OrientationAdministrative,
    QuestionComplementaire,
    ReponseComplementaire,
    SituationAdministrative,
    SuiviEtape,
    TypeQuestion,
)
from .serializers import (
    QuestionComplementaireSerializer,
    ReponsesComplementairesSerializer,
    SituationCreateSerializer,
    SituationHistorySerializer,
    SituationResultSerializer,
    SituationUpdateSerializer,
    SuiviEtapeUpdateSerializer,
    ChatQuestionSerializer
)

# Services utilisés pour communiquer avec AdmiGuide AI.
from .services.ai_service import (
    AIServiceError,
    transcrire_audio,
    interroger_chatbot
)
from .services.orientation_service import (
    OrientationServiceError,
    analyser_et_enregistrer,
)

from referentiel.models import EtapeDemarche

# Permet d'enregistrer plusieurs réponses dans une seule transaction.
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser

class AIServiceUnavailable(APIException):
    """Erreur retournée lorsque le microservice IA est indisponible."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Le service d'analyse est temporairement indisponible."
    default_code = "ai_service_unavailable"


def lancer_analyse(situation):
    """Lance l'analyse IA et transforme les erreurs techniques en erreurs API."""

    try:
        return analyser_et_enregistrer(situation)

    except AIServiceError as exc:
        raise AIServiceUnavailable() from exc

    except OrientationServiceError as exc:
        raise APIException(str(exc)) from exc


class AudioTranscriptionView(APIView):
    """
    Reçoit un enregistrement vocal et retourne
    sa transcription en texte.
    """

    # La saisie vocale est disponible sans compte,
    # comme le parcours d'orientation.
    permission_classes = [AllowAny]

    # Indique explicitement que cette route
    # reçoit un fichier en multipart/form-data.
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "audio": {
                        "type": "string",
                        "format": "binary",
                    }
                },
                "required": ["audio"],
            }
        },
    )
    def post(self, request):
        """Transmet l'audio au microservice AdmiGuide AI."""

        # Récupère le fichier envoyé dans le champ "audio".
        audio_file = request.FILES.get("audio")

        if audio_file is None:
            return Response(
                {
                    "detail": (
                        "Aucun fichier audio n'a été envoyé."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifie qu'il s'agit bien d'un contenu audio.
        content_type = (
            audio_file.content_type or ""
        )

        if not content_type.startswith("audio/"):
            return Response(
                {
                    "detail": (
                        "Le fichier envoyé doit être "
                        "un fichier audio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limite la taille de l'enregistrement à 10 Mo
        # afin d'éviter des fichiers inutilement volumineux.
        max_size = 10 * 1024 * 1024

        if audio_file.size > max_size:
            return Response(
                {
                    "detail": (
                        "Le fichier audio est trop volumineux."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = transcrire_audio(
                audio_file
            )

        except ValueError:
            return Response(
                {
                    "detail": (
                        "Le fichier audio envoyé est invalide."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except AIServiceError as exc:
            raise AIServiceUnavailable() from exc

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    
class SituationCreateView(generics.CreateAPIView):
    """
    Permet à un visiteur ou à un utilisateur connecté
    de décrire une situation administrative.
    """

    queryset = SituationAdministrative.objects.all()
    serializer_class = SituationCreateSerializer

    # Le parcours d'orientation est accessible sans compte.
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """Enregistre la situation uniquement si l'analyse aboutit."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Associe la situation au compte si l'utilisateur est connecté.
        if request.user.is_authenticated:
            situation = serializer.save(
                utilisateur=request.user,
            )
        else:
            situation = serializer.save()

        try:
            # Lance l'analyse avec AdmiGuide AI.
            analyse = lancer_analyse(situation)

        except Exception:
            # Ne conserve pas une situation dont l'analyse a échoué.
            situation.delete()
            raise

        # Retourne la situation ainsi que le résultat de l'analyse.
        donnees = dict(serializer.data)
        donnees["analyse"] = analyse

        return Response(
            donnees,
            status=status.HTTP_201_CREATED,
        )


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
    """Modifie une situation puis relance son analyse."""

    queryset = SituationAdministrative.objects.all()
    serializer_class = SituationUpdateSerializer
    permission_classes = [AllowAny]
    http_method_names = ["patch", "options"]
    lookup_field = "public_id"

    def get_object(self):
        """Retourne uniquement une situation que le demandeur peut modifier."""
        return get_accessible_situation(
            self.request,
            self.kwargs["public_id"],
        )

    def patch(self, request, *args, **kwargs):
        """Enregistre la nouvelle description et produit un résultat à jour."""
        situation = self.get_object()
        serializer = self.get_serializer(
            situation,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

            # Une nouvelle description invalide les anciennes réponses et le suivi.
            situation.questions.all().delete()

            try:
                situation.orientation.delete()
            except OrientationAdministrative.DoesNotExist:
                pass

        analyse = lancer_analyse(situation)

        return Response(
            {
                **serializer.data,
                "analyse": analyse,
            },
            status=status.HTTP_200_OK,
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

        # Retourne uniquement les questions encore sans réponse.
        return QuestionComplementaire.objects.filter(
            situation=situation,
            reponse__isnull=True,
        ).order_by("ordre")


class ReponseComplementaireView(generics.GenericAPIView):
    """
    Enregistre les réponses complémentaires
    fournies pour une situation.
    """

    serializer_class = ReponsesComplementairesSerializer
    permission_classes = [AllowAny]

    def post(self, request, public_id):
        """Valide et enregistre les précisions fournies."""

        # Vérifie que le demandeur peut accéder à cette situation.
        situation = get_accessible_situation(
            request,
            public_id,
        )

        # Valide les données reçues.
        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        reponses_a_enregistrer = []

        # Vérifie toutes les réponses
        # avant de modifier la base.
        for donnee in serializer.validated_data[
            "reponses"
        ]:

            try:
                # Vérifie que la question appartient
                # bien à cette situation.
                question = (
                    QuestionComplementaire.objects.get(
                        id=donnee["question_id"],
                        situation=situation,
                    )
                )

            except QuestionComplementaire.DoesNotExist:
                return Response(
                    {
                        "detail": (
                            f"La question "
                            f"{donnee['question_id']} "
                            "n'appartient pas à cette situation."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            contenu = donnee["contenu"]

            # Vérifie une réponse à choix unique.
            if (
                question.type_question
                == TypeQuestion.CHOIX_UNIQUE
                and contenu not in question.options
            ):
                return Response(
                    {
                        "detail": (
                            "Réponse invalide pour "
                            f"la question {question.id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            reponses_a_enregistrer.append(
                (question, contenu)
            )

        reponses_enregistrees = []

        # Enregistre toutes les réponses
        # dans une seule transaction.
        with transaction.atomic():

            for (
                question,
                contenu,
            ) in reponses_a_enregistrer:

                reponse, _ = (
                    ReponseComplementaire.objects
                    .update_or_create(
                        question=question,
                        defaults={
                            "contenu": contenu
                        },
                    )
                )

                reponses_enregistrees.append(
                    {
                        "question_id": question.id,
                        "contenu": reponse.contenu,
                    }
                )

        # Les nouvelles réponses peuvent modifier
        # le résultat de l'analyse.
        analyse = lancer_analyse(
            situation
        )

        return Response(
            {
                "detail": "Réponses enregistrées.",
                "reponses": reponses_enregistrees,
                "analyse": analyse,
            },
            status=status.HTTP_200_OK,
        )



class SuiviEtapeUpdateView(generics.GenericAPIView):
    """
    Permet à un utilisateur connecté de cocher
    ou décocher une étape de sa feuille de route.
    """

    serializer_class = SuiviEtapeUpdateSerializer
    permission_classes = [IsAuthenticated]

    # Seule la modification partielle est nécessaire.
    http_method_names = ["patch", "options"]

    def patch(self, request, public_id, etape_id):
        """Met à jour l'état d'une étape."""

        # La progression est réservée au propriétaire de la situation.
        situation = (
            SituationAdministrative.objects
            .filter(
                public_id=public_id,
                utilisateur=request.user,
            )
            .select_related(
                "orientation",
                "orientation__demarche",
            )
            .first()
        )

        if not situation:
            raise NotFound("Situation introuvable.")

        try:
            orientation = situation.orientation
        except OrientationAdministrative.DoesNotExist:
            raise NotFound("Orientation introuvable.")

        if not orientation.demarche:
            raise NotFound("Démarche introuvable.")

        # Vérifie que l'étape appartient bien à la démarche recommandée.
        try:
            etape = EtapeDemarche.objects.get(
                id=etape_id,
                demarche=orientation.demarche,
            )
        except EtapeDemarche.DoesNotExist:
            raise NotFound("Étape introuvable.")

        # Valide la valeur true/false reçue.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Crée le suivi ou met à jour celui qui existe déjà.
        suivi, _ = SuiviEtape.objects.update_or_create(
            orientation=orientation,
            etape=etape,
            defaults={
                "terminee": serializer.validated_data["terminee"],
            },
        )

        # Calcule la progression globale.
        total = orientation.demarche.etapes.count()

        terminees = SuiviEtape.objects.filter(
            orientation=orientation,
            etape__demarche=orientation.demarche,
            terminee=True,
        ).count()

        pourcentage = (
            round((terminees / total) * 100)
            if total > 0
            else 0
        )

        return Response(
            {
                "etape_id": etape.id,
                "terminee": suivi.terminee,
                "progression": {
                    "terminees": terminees,
                    "total": total,
                    "pourcentage": pourcentage,
                },
            },
            status=status.HTTP_200_OK,
        )



# ==========================================================
# CHATBOT CONTEXTUEL
# ==========================================================

class SituationChatView(APIView):
    """
    Permet de poser une question sur une situation existante.

    Django vérifie l'accès et prépare les informations
    avant de transmettre la demande à FastAPI.
    """

    permission_classes = [AllowAny]

    def post(self, request, public_id):
        """Traite une question du chatbot contextuel."""

        # Vérifie que la situation appartient à l'utilisateur
        # ou qu'elle est accessible en mode visiteur.
        situation = get_accessible_situation(
            request,
            public_id,
        )

        # Valide uniquement les champs autorisés.
        serializer = ChatQuestionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        donnees = serializer.validated_data
        page = donnees["page"]

        # Le chatbot de suivi est réservé au
        # propriétaire de la situation.
        if page == "SUIVI":
            if (
                not request.user.is_authenticated
                or situation.utilisateur_id != request.user.id
            ):
                raise NotFound("Situation introuvable.")

        # Informations de la question complémentaire.
        question_precision = None

        if page == "PRECISIONS":

            question_id = donnees.get("question_id")

            if question_id is None:
                return Response(
                    {"detail": "Identifiant de question requis."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # La question doit appartenir à la situation
            # et ne pas avoir déjà reçu une réponse.
            question_obj = QuestionComplementaire.objects.filter(
                id=question_id,
                situation=situation,
                reponse__isnull=True,
            ).first()

            if question_obj is None:
                raise NotFound(
                    "Question complémentaire introuvable."
                )

            question_precision = question_obj.texte

            # Le terme demandé doit être présent dans
            # la question ou dans ses choix proposés.
            terme = donnees.get("terme_juridique", "").strip()

            texte_question = " ".join([
                question_obj.texte,
                *(question_obj.options or []),
            ])

            if terme and terme.casefold() not in texte_question.casefold():
                return Response(
                    {"detail": "Terme absent de la question."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Récupère le résultat enregistré dans Django.
        resultat = SituationResultSerializer(situation).data

        if (
            page in ("RESULTAT", "SUIVI")
            and not resultat["demarche"]
        ):
            return Response(
                {"detail": "Aucune démarche disponible."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Détermine le domaine à partir du code métier.
        domaine = None

        if resultat["demarche"]:
            orientation = situation.orientation
            code = orientation.demarche.code

            if "PASSEPORT" in code:
                domaine = "PASSEPORT"
            elif "REVERSION" in code:
                domaine = "PENSION"
            elif "FONCIER" in code or "BAIL" in code:
                domaine = "FONCIER"

        # Prépare le contexte à partir de données fiables
        # enregistrées dans la base Django.
        contexte = {
            "question": donnees["question"],
            "page": page,
            "situation": situation.description_initiale,
            "domaine": domaine,
            "demarche": (
                resultat["demarche"]["intitule"]
                if resultat["demarche"]
                else None
            ),
            "etapes": [
                etape["description"]
                for etape in resultat["etapes"][:30]
            ],
            "pieces_a_preparer": [
                piece["libelle"]
                for piece in resultat["pieces_a_preparer"][:50]
            ],
            "services_competents": (
                resultat["services_competents"][:10]
            ),
            "question_precision": question_precision,
            "terme_juridique": donnees.get("terme_juridique"),
            "historique": donnees.get("historique", []),
        }

        try:
            # Communique avec le chatbot FastAPI.
            reponse = interroger_chatbot(contexte)

        except AIServiceError as exc:
            raise AIServiceUnavailable() from exc

        return Response(
            reponse,
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