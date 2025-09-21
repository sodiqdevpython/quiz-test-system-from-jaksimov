from django.db import models
from mainApp.models import Group, User
import pandas as pd


class StudentImport(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="Guruh")
    file = models.FileField(upload_to="imports/", verbose_name="Excel fayl")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Import - {self.group.name} ({self.created_at:%Y-%m-%d %H:%M})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        df = pd.read_excel(self.file.path)

        for _, row in df.iterrows():
            talaba_id = str(row["Talaba ID"]).strip()
            passport = str(row["Pasport raqami"]).strip()
            fullname = str(row["To‘liq ismi"]).strip()

            # Familiya va ismni ajratish
            parts = fullname.split()
            last_name = parts[0] if len(parts) > 0 else ""
            first_name = parts[1] if len(parts) > 1 else ""

            # User yaratish yoki mavjud bo‘lsa olish
            user, created = User.objects.get_or_create(
                username=talaba_id,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": "",
                }
            )
            if created:
                user.set_password(passport)
                user.role = "Talaba"
                user.group = self.group
                user.save()