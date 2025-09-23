from django.db.models.signals import post_save
from django.dispatch import receiver
from mainApp.models import Theme, Test, User
from .tasks import send_push_to_users


@receiver(post_save, sender=Theme)
def notify_new_theme(sender, instance, created, **kwargs):
    if not created:
        return

    subject = instance.subject
    groups = subject.groups.all()

    # Guruh talabalari va authorlari
    students = User.objects.filter(group__in=groups, role="student")
    authors = User.objects.filter(group__in=groups, role="teacher")

    receivers = students.union(authors)
    user_ids = list(receivers.values_list("id", flat=True))

    send_push_to_users.delay(
        user_ids,
        "Yangi mavzu",
        f"'{instance.name}' mavzusi {subject.name} faniga qo‘shildi"
    )


@receiver(post_save, sender=Test)
def notify_new_test(sender, instance, created, **kwargs):
    if not created:
        return
    print("keldi")
    subject = instance.theme.subject
    groups = subject.groups.all()

    # Guruh talabalari va authorlari
    students = User.objects.filter(group__in=groups, role="student")
    authors = User.objects.filter(group__in=groups, role="teacher")

    receivers = students.union(authors)
    user_ids = list(receivers.values_list("id", flat=True))

    send_push_to_users.delay(
        user_ids,
        "Yangi test",
        f"'{instance.name}' testi '{instance.theme.name}' mavzusiga qo‘shildi!"
    )
