from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from banking.models import VirtualBankAccount
from loans.models import LoanRateTier


def env_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


class Command(BaseCommand):
    help = 'Create missing SACCO online defaults without deleting existing data.'

    def add_arguments(self, parser):
        parser.add_argument('--admin-username')
        parser.add_argument('--admin-email')
        parser.add_argument('--admin-password')
        parser.add_argument('--member-username')
        parser.add_argument('--member-email')
        parser.add_argument('--member-password')
        parser.add_argument('--bank-balance')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        admin_username = options['admin_username'] or self._env('SACCO_ADMIN_USERNAME', 'admin')
        admin_email = options['admin_email'] or self._env('SACCO_ADMIN_EMAIL', 'admin@sacco.local')
        admin_password = options['admin_password'] or self._env('SACCO_ADMIN_PASSWORD', 'admin123')
        member_username = options['member_username'] or self._env('SACCO_MEMBER_USERNAME', 'member')
        member_email = options['member_email'] or self._env('SACCO_MEMBER_EMAIL', 'member@sacco.local')
        member_password = options['member_password'] or self._env('SACCO_MEMBER_PASSWORD', 'member123')
        bank_balance = Decimal(options['bank_balance'] or self._env('SACCO_BANK_BALANCE', '1000000.00'))

        admin, admin_created = self._ensure_user(
            User,
            username=admin_username,
            email=admin_email,
            password=admin_password,
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True,
            position='System Administrator',
        )
        member, member_created = self._ensure_user(
            User,
            username=member_username,
            email=member_email,
            password=member_password,
            role=User.MEMBER,
            is_staff=False,
            is_superuser=False,
            phone=self._env('SACCO_MEMBER_PHONE', '0700000000'),
        )

        for member_data in self._extra_members():
            self._ensure_user(
                User,
                username=member_data['username'],
                email=member_data['email'],
                password=member_data['password'],
                role=User.MEMBER,
                is_staff=False,
                is_superuser=False,
                phone=member_data.get('phone', ''),
            )

        bank, bank_created = VirtualBankAccount.objects.get_or_create(
            name='SACCO Virtual Bank',
            defaults={'balance': bank_balance, 'is_active': True},
        )
        if not bank.is_active:
            bank.is_active = True
            bank.save(update_fields=('is_active', 'updated_at'))

        self._ensure_loan_tiers()

        self.stdout.write(self.style.SUCCESS('SACCO online defaults are ready.'))
        self._print_user_status('Admin', admin, admin_created, admin_password)
        self._print_user_status('Member', member, member_created, member_password)
        if bank_created:
            self.stdout.write(f'Virtual bank created with balance {bank.balance}.')

    def _env(self, name, default=''):
        import os

        return os.environ.get(name, default).strip()

    def _ensure_user(self, User, **data):
        password = data.pop('password')
        username = data.pop('username')
        user, created = User.objects.get_or_create(username=username, defaults=data)
        changed_fields = []

        if created:
            user.set_password(password)
            user.save()
            return user, created

        for field, value in data.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed_fields.append(field)

        if changed_fields:
            user.save(update_fields=changed_fields)

        return user, created

    def _extra_members(self):
        raw_members = self._env('SACCO_EXTRA_MEMBERS')
        members = []
        for raw_member in raw_members.split(','):
            parts = [part.strip() for part in raw_member.split(':')]
            if not parts or not parts[0]:
                continue
            members.append(
                {
                    'username': parts[0],
                    'email': parts[1] if len(parts) > 1 else f'{parts[0]}@sacco.local',
                    'password': parts[2] if len(parts) > 2 else self._env('SACCO_MEMBER_PASSWORD', 'member123'),
                    'phone': parts[3] if len(parts) > 3 else '',
                }
            )
        return members

    def _ensure_loan_tiers(self):
        tiers = (
            ('Small Loan', Decimal('1000.00'), Decimal('50000.00'), Decimal('5.00')),
            ('Standard Loan', Decimal('50001.00'), Decimal('250000.00'), Decimal('8.00')),
            ('Large Loan', Decimal('250001.00'), Decimal('1000000.00'), Decimal('10.00')),
        )
        for name, min_amount, max_amount, interest_rate in tiers:
            LoanRateTier.objects.update_or_create(
                name=name,
                defaults={
                    'min_amount': min_amount,
                    'max_amount': max_amount,
                    'interest_rate': interest_rate,
                    'is_active': True,
                },
            )

    def _print_user_status(self, label, user, created, password):
        action = 'created' if created else 'already exists'
        self.stdout.write(f'{label} {action}: {user.username}')
        if created:
            self.stdout.write(f'{label} initial password: {password}')
