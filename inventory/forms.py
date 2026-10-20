from django import forms
from .models import Category, Location, Item, AssetUnit


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: Elektronik & Kamera'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: Gudang BMN Gedung A Lt. 1'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            'code', 'name', 'category', 'item_type', 'unit',
            'location', 'brand', 'description',
            'stock_available', 'minimum_stock', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: BRG-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama barang'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit / Rim / Box / Buah'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sony, Canon, PaperOne, dll.'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'stock_available': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StockAdjustmentForm(forms.Form):
    new_available = forms.IntegerField(
        min_value=0,
        label="Jumlah Stok Fisik Tersedia Baru",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        label="Alasan Penyesuaian Stok (Wajib)",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Contoh: Hasil Stock Opname Triwulan III...'})
    )


class AssetUnitForm(forms.ModelForm):
    class Meta:
        model = AssetUnit
        fields = ['asset_code', 'serial_number', 'condition', 'status', 'location', 'notes']
        widgets = {
            'asset_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kode NUP / Barcode'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
