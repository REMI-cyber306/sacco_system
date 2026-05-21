from django.core.mail import send_mail
from django.conf import settings
from .models import Notification


def notify_user(user, subject, message):
    # Always save notification in DB
    Notification.objects.create(member=user, message=message)

    # Send email safely (never crash app if email fails)
    if user.email:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )
        except Exception as e:
            print("Email failed:", e)


def notify_users(users, subject, message):
    for user in users:
        notify_user(user, subject, message)
