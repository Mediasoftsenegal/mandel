from django.contrib import admin

from .models import PhotoModele


@admin.register(PhotoModele)
class PhotoModeleAdmin(admin.ModelAdmin):
    list_display = ('modele_id', 'societe')
