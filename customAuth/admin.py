from django.contrib import admin
from .models import StudentImport

@admin.register(StudentImport)
class StudentImportAdmin(admin.ModelAdmin):
    list_display = ("group", "file", "created_at")
    readonly_fields = ("created_at",)