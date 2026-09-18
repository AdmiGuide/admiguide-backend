"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Routes liées à l'authentification et aux comptes utilisateurs.
    path("api/auth/", include("accounts.urls")),

    # Interface Swagger permettant de consulter et tester les endpoints.
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Routes liées au parcours d'orientation administrative.
    path("api/orientations/", include("orientations.urls")),

    # Routes du référentiel et des sources administratives.
    path("api/referentiel/", include("referentiel.urls")),

    # Routes liées aux signalements des usagers.
    path("api/signalements/", include("signalements.urls")),

    # Génère le schéma OpenAPI utilisé par la documentation.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]
