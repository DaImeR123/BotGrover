from django.contrib import admin
from .models import Culture, Planting

@admin.register(Culture)
class CultureAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'grams_per_tray',
        'soaking_required',
        'press_weight',
        'germination_days',
        'light_days',
        'grow_days',
        'expire_days'
    )
    list_filter = ('soaking_required', 'press_weight')

@admin.register(Planting)
class PlantingAdmin(admin.ModelAdmin):
    list_display = (
        'culture',
        'plant_date',
        'harvest_date',
        'sale_deadline',
        'status',
        'quantity'
    )
    list_filter = ('status', 'culture')
    readonly_fields = ('harvest_date', 'sale_deadline')
    search_fields = ('culture__name',)