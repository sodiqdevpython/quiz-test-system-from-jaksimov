import os, time
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from mainApp.models import User
from .models import StudentImport
import pandas as pd

@shared_task
def send_reset_email(email, token):
    reset_link = f"http://192.168.1.133:5173/reset-password/{token}"
    subject = "Parolni tiklash"
    message = (
        f"\n\nParolingizni tiklash uchun quyidagi linkdan foydalaning:\n"
        f"{reset_link}\n\nAgar parolingizni almashtirmoqchi bo'lmasangiz e'tiborsiz qoldiring.\n bu link 10 daqiqa davomida yaroqli bo'la oladi !"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    
@shared_task
def process_student_import(import_id):
    try:
        student_import = StudentImport.objects.get(id=import_id)
    except StudentImport.DoesNotExist:
        return "Import topilmadi"

    for _ in range(5):
        if os.path.exists(student_import.file.path):
            break
        time.sleep(1)
    if not os.path.exists(student_import.file.path):
        return "Fayl topilmadi"

    df = pd.read_excel(student_import.file.path)
    count = 0

    for _, row in df.iterrows():
        talaba_id = str(row["Talaba ID"]).strip()
        passport = str(row["Pasport raqami"]).strip()
        fullname = str(row["To‘liq ismi"]).strip()

        parts = fullname.split()
        last_name = parts[0] if len(parts) > 0 else ""
        first_name = parts[1] if len(parts) > 1 else ""

        user, created = User.objects.get_or_create(
            username=talaba_id,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": "",
            }
        )

        user.set_password(passport)
        user.role = "student"
        user.group = student_import.group
        user.save()
        count += 1

    return f"{count} ta yangi user yaratildi"

