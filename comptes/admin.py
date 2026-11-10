from django.contrib import admin

from .models import ProfilCompte


@admin.register(ProfilCompte)
class ProfilCompteAdmin(admin.ModelAdmin):
    list_display = ('user', 'profil', 'legacy_id', 'id_societe')
    list_filter = ('profil',)
