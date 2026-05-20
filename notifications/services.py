from django.core.mail import send_mail

from .models import Notification


def notify_user(user, subject, message):
    Notification.objects.create(member=user, message=message)
    if user.email:
        send_mail(subject, message, None, [user.email], fail_silently=True)


def notify_users(users, subject, message):
    for user in users:
        notify_user(user, subject, message)
