from django import forms

from users.models import User

from .models import Loan, LoanCollateral, LoanGuarantor, LoanRateTier


class LoanApplicationForm(forms.ModelForm):
    requested_disbursement_date = forms.DateField(
        label='Preferred loan release date',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    repayment_start_date = forms.DateField(
        label='Preferred repayment start date',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    property_name = forms.CharField(max_length=100)
    estimated_value = forms.DecimalField(max_digits=18, decimal_places=2)
    collateral_description = forms.CharField(widget=forms.Textarea)
    guarantor_1 = forms.ModelChoiceField(queryset=User.objects.none(), required=True)
    guarantor_1_relationship = forms.CharField(max_length=50, required=False)
    guarantor_2 = forms.ModelChoiceField(queryset=User.objects.none(), required=False)
    guarantor_2_relationship = forms.CharField(max_length=50, required=False)

    class Meta:
        model = Loan
        fields = (
            'amount',
            'duration_months',
            'requested_disbursement_date',
            'repayment_start_date',
            'purpose',
        )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        members = User.objects.filter(role=User.MEMBER, is_staff=False)
        if user is not None:
            members = members.exclude(pk=user.pk)
        self.fields['guarantor_1'].queryset = members
        self.fields['guarantor_2'].queryset = members
        self.fields['property_name'].label = 'Property pledged as collateral'
        self.fields['estimated_value'].label = 'Estimated property value'
        self.fields['collateral_description'].label = 'Property description'
        self.fields['guarantor_1'].label = 'First SACCO member guarantor'
        self.fields['guarantor_2'].label = 'Second SACCO member guarantor'
        self.fields['amount'].help_text = 'The interest rate is selected automatically from the SACCO loan brackets.'

    def clean(self):
        cleaned_data = super().clean()
        guarantor_1 = cleaned_data.get('guarantor_1')
        guarantor_2 = cleaned_data.get('guarantor_2')
        amount = cleaned_data.get('amount')
        requested_disbursement_date = cleaned_data.get('requested_disbursement_date')
        repayment_start_date = cleaned_data.get('repayment_start_date')

        if guarantor_1 and guarantor_2 and guarantor_1 == guarantor_2:
            raise forms.ValidationError('Choose two different guarantors.')

        if amount and not LoanRateTier.for_amount(amount):
            raise forms.ValidationError('No active loan interest bracket covers this amount.')

        if requested_disbursement_date and repayment_start_date:
            if repayment_start_date < requested_disbursement_date:
                raise forms.ValidationError('Repayment start date cannot be before the loan release date.')

        return cleaned_data

    def save_application(self, member):
        loan = super().save(commit=False)
        loan.member = member
        loan_rate = LoanRateTier.for_amount(loan.amount)
        loan.interest_rate = loan_rate.interest_rate
        loan.save()

        LoanCollateral.objects.create(
            loan=loan,
            property_name=self.cleaned_data['property_name'],
            estimated_value=self.cleaned_data['estimated_value'],
            description=self.cleaned_data['collateral_description'],
        )

        guarantors = [
            ('guarantor_1', 'guarantor_1_relationship'),
            ('guarantor_2', 'guarantor_2_relationship'),
        ]
        for guarantor_field, relationship_field in guarantors:
            guarantor = self.cleaned_data.get(guarantor_field)
            if guarantor:
                LoanGuarantor.objects.create(
                    loan=loan,
                    guarantor=guarantor,
                    relationship=self.cleaned_data.get(relationship_field, ''),
                )

        return loan
