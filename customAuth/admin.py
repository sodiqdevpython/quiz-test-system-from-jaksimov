from django.contrib import admin
from .models import StudentImport
from .tasks import process_student_import

@admin.register(StudentImport)
class StudentImportAdmin(admin.ModelAdmin):
    list_display = ("group", "file", "created",)
    readonly_fields = ("created",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        process_student_import.delay(obj.id)
        self.message_user(request, "Fayl yuklandi, userlar orqa fonda yaratilmoqda ✅")