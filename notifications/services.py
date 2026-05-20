from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def notify_user(user, subject, message):
    Notification.objects.create(member=user, message=message)
    if user.email:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=settings.EMAIL_FAIL_SILENTLY,
        )


def notify_users(users, subject, message):
    for user in users:
        notify_user(user, subject, message)
