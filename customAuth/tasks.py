from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task

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