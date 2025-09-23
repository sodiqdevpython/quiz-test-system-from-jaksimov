from django.db import models
from mainApp.models import Group
from utils.models import BaseModel

class StudentImport(BaseModel):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="Guruh")
    file = models.FileField(upload_to="imports/", verbose_name="Excel fayl")

    def __str__(self):
        return f"Import - {self.group.name} ({self.created:%Y-%m-%d %H:%M})"