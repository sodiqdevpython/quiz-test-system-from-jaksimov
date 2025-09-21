from django.db import models
from utils.models import BaseModel
from mainApp.models import User

class DeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DeviceToken({self.user.username})"