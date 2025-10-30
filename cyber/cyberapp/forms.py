from django import forms
from .models import Student, Payment

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['firstname', 'lastname', 'idnumber', 'phonenumber']
        widgets = {
            'firstname': forms.TextInput(attrs={'class': 'form-control'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control'}),
            'idnumber': forms.NumberInput(attrs={'class': 'form-control'}),
            'phonenumber': forms.NumberInput(attrs={'class': 'form-control'}),
        }
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'balance', 'date', 'student']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'student': forms.Select(attrs={'class': 'form-control'}),
        }
        