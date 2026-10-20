from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import LoanRequest, LoanItem, LoanHandover, ReturnRecord
from inventory.models import Item


class LoanApplyForm(forms.ModelForm):
    class Meta:
        model = LoanRequest
        fields = ['start_date', 'due_date', 'purpose']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Keperluan dinas, kegiatan liputan, pengukuran lapangan, dll.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.now().date()
        self.fields['start_date'].initial = today
        self.fields['due_date'].initial = today + timezone.timedelta(days=3)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        due = cleaned_data.get('due_date')
        if start and due and due < start:
            self.add_error('due_date', "Tanggal jatuh tempo tidak boleh mendahului tanggal mulai pinjam.")
        return cleaned_data


class BaseLoanItemForm(forms.ModelForm):
    class Meta:
        model = LoanItem
        fields = ['item', 'quantity_requested', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'quantity_requested': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Catatan khusus'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ONLY active LOANABLE items can be selected!
        self.fields['item'].queryset = Item.objects.filter(
            item_type=Item.ItemType.LOANABLE,
            is_active=True
        ).order_by('name')


LoanItemFormSet = inlineformset_factory(
    LoanRequest,
    LoanItem,
    form=BaseLoanItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class LoanReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('APPROVE', 'Setujui Pengajuan'),
        ('REJECT', 'Tolak Pengajuan'),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect(attrs={'class': 'btn-check'}))
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Wajib diisi jika menolak...'}),
        label="Alasan Penolakan"
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reason = cleaned_data.get('rejection_reason', '').strip()
        if action == 'REJECT' and not reason:
            self.add_error('rejection_reason', "Alasan penolakan wajib diisi bila menolak pengajuan.")
        return cleaned_data


class LoanCancelForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alasan pembatalan...'}),
        label="Alasan Pembatalan"
    )
