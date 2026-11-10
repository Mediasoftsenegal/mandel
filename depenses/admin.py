from django.contrib import admin

from .models import Depense


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ('date_depense', 'nom', 'objet', 'montant')
    list_filter = ('date_depense',)
