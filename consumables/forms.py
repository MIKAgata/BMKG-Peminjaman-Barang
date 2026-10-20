from django import forms
from django.forms import inlineformset_factory
from .models import ConsumableHandover, ConsumableHandoverItem
from inventory.models import Item
from accounts.models import CustomUser


class ConsumableHandoverForm(forms.ModelForm):
    class Meta:
        model = ConsumableHandover
        fields = ['recipient', 'department', 'purpose', 'notes']
        widgets = {
            'recipient': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit kerja / seksi penerima'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Kebutuhan rapat, operasional kantor, dll.'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'username')


class BaseConsumableItemForm(forms.ModelForm):
    class Meta:
        model = ConsumableHandoverItem
        fields = ['item', 'quantity', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Catatan'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ONLY active CONSUMABLE items
        self.fields['item'].queryset = Item.objects.filter(
            item_type=Item.ItemType.CONSUMABLE,
            is_active=True
        ).order_by('name')


ConsumableItemFormSet = inlineformset_factory(
    ConsumableHandover,
    ConsumableHandoverItem,
    form=BaseConsumableItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)
