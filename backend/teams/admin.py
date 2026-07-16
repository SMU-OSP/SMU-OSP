from django.contrib import admin

from .models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "leader", "updated_at")
    search_fields = ("name", "leader__username", "leader__name")
