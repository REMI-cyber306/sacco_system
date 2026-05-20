from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from banking.models import BankTransaction, VirtualBankAccount
from loans.models import Loan, LoanCollateral, LoanGuarantor, LoanRateTier
from notifications.models import Notification
from penalties.models import Penalty
from repayments.models import Repayment


class Command(BaseCommand):
    help = 'Clear SACCO demo data and recreate clean admin/member logins.'

    def add_arguments(self, parser):
        parser.add_argument('--admin-username', default='admin')
        parser.add_argument('--admin-password', default='admin123')
        parser.add_argument('--member-username', default='member')
        parser.add_argument('--member-password', default='member123')
        parser.add_argument('--bank-balance', default='1000000.00')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        Penalty.objects.all().delete()
        BankTransaction.objects.all().delete()
        Repayment.objects.all().delete()
        LoanCollateral.objects.all().delete()
        LoanGuarantor.objects.all().delete()
        Loan.objects.all().delete()
        Notification.objects.all().delete()
        VirtualBankAccount.objects.all().delete()
        User.objects.all().delete()
        LoanRateTier.objects.all().delete()

        admin = User.objects.create_superuser(
            username=options['admin_username'],
            password=options['admin_password'],
            email='admin@sacco.local',
            role=User.ADMIN,
            position='System Administrator',
        )
        member = User.objects.create_user(
            username=options['member_username'],
            password=options['member_password'],
            email='member@sacco.local',
            role=User.MEMBER,
            phone='0700000000',
            savings_balance=Decimal('0.00'),
        )

        VirtualBankAccount.objects.create(
            name='SACCO Virtual Bank',
            balance=Decimal(options['bank_balance']),
            is_active=True,
        )

        LoanRateTier.objects.bulk_create(
            [
                LoanRateTier(
                    name='Small Loan',
                    min_amount=Decimal('1000.00'),
                    max_amount=Decimal('50000.00'),
                    interest_rate=Decimal('5.00'),
                    is_active=True,
                ),
                LoanRateTier(
                    name='Standard Loan',
                    min_amount=Decimal('50001.00'),
                    max_amount=Decimal('250000.00'),
                    interest_rate=Decimal('8.00'),
                    is_active=True,
                ),
                LoanRateTier(
                    name='Large Loan',
                    min_amount=Decimal('250001.00'),
                    max_amount=Decimal('1000000.00'),
                    interest_rate=Decimal('10.00'),
                    is_active=True,
                ),
            ]
        )

        self.stdout.write(self.style.SUCCESS('SACCO system reset complete.'))
        self.stdout.write(f'Admin login: {admin.username} / {options["admin_password"]}')
        self.stdout.write(f'Member login: {member.username} / {options["member_password"]}')
