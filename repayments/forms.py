from django import forms

from .models import Repayment


class RepaymentForm(forms.ModelForm):
    class Meta:
        model = Repayment
        fields = ('loan', 'amount_paid', 'payment_method')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not user.is_staff and getattr(user, 'role', None) != 'admin':
            self.fields['loan'].queryset = self.fields['loan'].queryset.filter(member=user)

