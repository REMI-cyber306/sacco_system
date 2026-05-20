from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ADMIN = 'admin'
    MEMBER = 'member'

    ROLE_CHOICES = (
        (ADMIN, 'Admin'),
        (MEMBER, 'Member'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=MEMBER)
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=50, blank=True)
    savings_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_sacco_admin(self):
        return self.is_superuser or self.is_staff or self.role == self.ADMIN

    @property
    def is_sacco_member(self):
        return self.role == self.MEMBER and not self.is_sacco_admin

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.ADMIN
            self.is_staff = True
        elif self.role == self.ADMIN:
            self.is_staff = True
        elif self.role == self.MEMBER:
            self.is_staff = False
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
