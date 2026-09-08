from django.contrib import admin

from .models import (
    OrientationAdministrative,
    QuestionComplementaire,
    ReponseComplementaire,
    SituationAdministrative,
)

# Permet de consulter les données d'orientation depuis l'administration Django.
admin.site.register(
    [
        SituationAdministrative,
        QuestionComplementaire,
        ReponseComplementaire,
        OrientationAdministrative,
    ]
)
