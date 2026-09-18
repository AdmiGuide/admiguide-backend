from django.contrib import admin

from .models import Signalement, TraitementSignalement


admin.site.register(Signalement)
admin.site.register(TraitementSignalement)
