from django.contrib import admin

from .models import ScoreModele


@admin.register(ScoreModele)
class ScoreModeleAdmin(admin.ModelAdmin):
    list_display = ('modele_id', 'score', 'societe')
    ordering = ('-score',)
