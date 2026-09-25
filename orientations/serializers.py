from rest_framework import serializers

from .models import (
    OrientationAdministrative,
    QuestionComplementaire,
    SituationAdministrative,
    SuiviEtape,
)
from referentiel.models import StatutSource


class SituationCreateSerializer(serializers.ModelSerializer):
    """Sérialise une situation administrative décrite par un usager."""

    class Meta:
        model = SituationAdministrative
        fields = [
            "id",
            "public_id",
            "description_initiale",
            "pays_residence",
            "pays_application",
            "date_creation",
        ]
        read_only_fields = ["id", "public_id", "date_creation"]


class SituationResultSerializer(serializers.ModelSerializer):
    """Sérialise le résultat complet de l'orientation."""

    orientation_disponible = serializers.SerializerMethodField()
    demarche = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()
    avertissement = serializers.SerializerMethodField()
    etapes = serializers.SerializerMethodField()
    progression = serializers.SerializerMethodField()
    pieces_a_preparer = serializers.SerializerMethodField()
    services_competents = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()

    class Meta:
        model = SituationAdministrative
        fields = [
            "public_id",
            "description_initiale",
            "pays_application",
            "pays_residence",
            "date_creation",
            "orientation_disponible",
            "demarche",
            "resume",
            "avertissement",
            "etapes",
            "progression",
            "pieces_a_preparer",
            "services_competents",
            "sources",
        ]

    def _get_orientation(self, obj):
        """Retourne l'orientation associée si elle existe."""
        try:
            return obj.orientation
        except OrientationAdministrative.DoesNotExist:
            return None

    def _get_demarche(self, obj):
        """Retourne la démarche recommandée si elle existe."""
        orientation = self._get_orientation(obj)
        if orientation and orientation.demarche:
            return orientation.demarche
        return None

    def get_orientation_disponible(self, obj):
        """Indique si l'analyse a déjà produit une orientation."""
        return self._get_orientation(obj) is not None

    def get_demarche(self, obj):
        """Retourne les informations principales de la démarche."""
        demarche = self._get_demarche(obj)
        if not demarche:
            return None

        return {
            "id": demarche.id,
            "intitule": demarche.intitule,
            "description": demarche.description,
            "cout_indicatif": demarche.cout_indicatif,
            "delai_indicatif": demarche.delai_indicatif,
        }

    def get_resume(self, obj):
        """Retourne le résumé généré pour l'usager."""
        orientation = self._get_orientation(obj)
        return orientation.resume if orientation else None

    def get_avertissement(self, obj):
        """Retourne l'avertissement associé au résultat."""
        orientation = self._get_orientation(obj)
        return orientation.avertissement if orientation else None

    def get_etapes(self, obj):
        """Retourne les étapes avec leur état d'avancement."""
        orientation = self._get_orientation(obj)
        demarche = self._get_demarche(obj)

        if not orientation or not demarche:
            return []

        suivis = {
            suivi.etape_id: suivi.terminee
            for suivi in SuiviEtape.objects.filter(orientation=orientation)
        }

        return [
            {
                "id": etape.id,
                "ordre": etape.ordre,
                "description": etape.description,
                "terminee": suivis.get(etape.id, False),
            }
            for etape in demarche.etapes.all()
        ]

    def get_progression(self, obj):
        """Calcule la progression globale de la feuille de route."""
        orientation = self._get_orientation(obj)
        demarche = self._get_demarche(obj)

        if not orientation or not demarche:
            return {"terminees": 0, "total": 0, "pourcentage": 0}

        total = demarche.etapes.count()
        terminees = SuiviEtape.objects.filter(
            orientation=orientation,
            etape__demarche=demarche,
            terminee=True,
        ).count()

        pourcentage = round((terminees / total) * 100) if total else 0

        return {
            "terminees": terminees,
            "total": total,
            "pourcentage": pourcentage,
        }

    def get_pieces_a_preparer(self, obj):
        """Retourne les pièces et informations nécessaires."""
        demarche = self._get_demarche(obj)
        if not demarche:
            return []

        return [
            {
                "libelle": piece.libelle,
                "obligatoire": piece.obligatoire,
            }
            for piece in demarche.pieces_requises.all()
        ]

    def get_services_competents(self, obj):
        """Retourne les services pouvant traiter la démarche."""
        demarche = self._get_demarche(obj)
        if not demarche:
            return []

        return [
            {
                "nom": service.nom,
                "administration": service.administration.nom,
                "adresse": service.adresse,
                "contact": service.contact,
            }
            for service in demarche.services.select_related(
                "administration"
            ).all()
        ]

    def get_sources(self, obj):
        """Retourne uniquement les sources actuellement disponibles."""
        demarche = self._get_demarche(obj)
        if not demarche:
            return []

        sources = demarche.sources.filter(
            statut=StatutSource.DISPONIBLE
        ).order_by("titre")

        return [
            {
                "titre": source.titre,
                "url": source.url,
            }
            for source in sources
        ]


class SituationHistorySerializer(serializers.ModelSerializer):
    """Sérialise une situation pour l'écran « Mon historique »."""

    titre = serializers.SerializerMethodField()
    pays_residence = serializers.SerializerMethodField()
    orientation_disponible = serializers.SerializerMethodField()

    class Meta:
        model = SituationAdministrative
        fields = [
            "public_id",
            "titre",
            "pays_application",
            "pays_residence",
            "date_creation",
            "orientation_disponible",
        ]

    def _get_orientation(self, obj):
        """Retourne l'orientation si elle existe."""
        try:
            return obj.orientation
        except OrientationAdministrative.DoesNotExist:
            return None

    def get_titre(self, obj):
        """Utilise l'intitulé de la démarche quand il est disponible."""
        orientation = self._get_orientation(obj)

        if orientation and orientation.demarche:
            return orientation.demarche.intitule

        texte = obj.description_initiale.strip()
        return f"{texte[:60]}..." if len(texte) > 60 else texte

    def get_pays_residence(self, obj):
        """Retourne le pays enregistré dans le profil utilisateur."""
        if obj.utilisateur:
            return obj.utilisateur.pays_residence
        return None

    def get_orientation_disponible(self, obj):
        """Indique si la situation possède déjà une orientation."""
        return self._get_orientation(obj) is not None


class QuestionComplementaireSerializer(serializers.ModelSerializer):
    """Sérialise une question complémentaire destinée au frontend."""

    class Meta:
        model = QuestionComplementaire
        fields = [
            "id",
            "texte",
            "ordre",
            "type_question",
            "options",
        ]


class ReponseComplementaireInputSerializer(serializers.Serializer):
    """Valide une réponse envoyée par l'utilisateur."""

    question_id = serializers.IntegerField()
    contenu = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )


class ReponsesComplementairesSerializer(serializers.Serializer):
    """Valide les précisions fournies pour une situation."""

    pays_residence = serializers.CharField(
        max_length=100,
        allow_blank=False,
        trim_whitespace=True,
    )

    reponses = ReponseComplementaireInputSerializer(
        many=True,
        allow_empty=True,
    )


class SituationUpdateSerializer(serializers.ModelSerializer):
    """Valide la modification de la description d'une situation."""

    class Meta:
        model = SituationAdministrative
        fields = ["description_initiale"]


class SuiviEtapeUpdateSerializer(serializers.Serializer):
    """Valide l'état d'une étape de la feuille de route."""

    terminee = serializers.BooleanField()
