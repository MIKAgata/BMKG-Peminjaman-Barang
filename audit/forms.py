from django import forms
from .models import InstitutionSetting


class InstitutionSettingForm(forms.ModelForm):
    class Meta:
        model = InstitutionSetting
        fields = [
            'institution_name', 'unit_name', 'address', 'phone', 'email',
            'head_officer_name', 'head_officer_nip',
            'warehouse_officer_name', 'warehouse_officer_nip'
        ]
        widgets = {
            'institution_name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'head_officer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'head_officer_nip': forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse_officer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse_officer_nip': forms.TextInput(attrs={'class': 'form-control'}),
        }
