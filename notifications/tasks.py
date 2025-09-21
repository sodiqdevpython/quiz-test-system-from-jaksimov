from celery import shared_task
from notifications.models import DeviceToken
from utils.push_fcm import send_push_fcm

@shared_task
def send_push_to_users(user_ids, title, body):
    from mainApp.models import User  # ichida import qilamiz
    users = User.objects.filter(id__in=user_ids)
    for user in users:
        for dev in DeviceToken.objects.filter(user=user):
            send_push_fcm(dev.token, title, body)
