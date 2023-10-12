from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "created_user",
        "team",
    )

    search_fields = (
        "title",
        "=created_user__username",
    )
