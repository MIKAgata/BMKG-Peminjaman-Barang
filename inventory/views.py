from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import ValidationError

from accounts.permissions import admin_required
from .models import Category, Location, Item, AssetUnit, StockMovement
from .forms import CategoryForm, LocationForm, ItemForm, StockAdjustmentForm, AssetUnitForm
from .services import InventoryService
from audit.utils import log_action
from audit.models import AuditLog


# --- Master Barang ---

@login_required
@admin_required
def item_list_view(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    item_type = request.GET.get('type', '').strip()
    status = request.GET.get('status', '').strip()
    low_stock = request.GET.get('low_stock', '').strip()

    items = Item.objects.select_related('category', 'location').all()

    if query:
        items = items.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(brand__icontains=query)
        )
    if category_id:
        items = items.filter(category_id=category_id)
    if item_type:
        items = items.filter(item_type=item_type)
    if status != '':
        items = items.filter(is_active=(status == '1'))
    if low_stock == '1':
        items = [i for i in items if i.is_low_stock]

    if not isinstance(items, list):
        paginator = Paginator(items, 15)
    else:
        paginator = Paginator(items, 15)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(is_active=True)

    return render(request, 'inventory/item_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'item_types': Item.ItemType.choices,
        'query': query,
        'selected_category': category_id,
        'selected_type': item_type,
        'selected_status': status,
        'selected_low_stock': low_stock,
    })


@login_required
@admin_required
def item_create_view(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            # If initial stock > 0, log it in StockMovement
            if item.stock_available > 0:
                StockMovement.objects.create(
                    item=item,
                    movement_type=StockMovement.MovementType.INITIAL,
                    quantity=item.stock_available,
                    stock_available_before=0,
                    stock_available_after=item.stock_available,
                    stock_loaned_before=0,
                    stock_loaned_after=0,
                    reference_number=f"INIT-{item.code}",
                    created_by=request.user,
                    reason="Saldo awal saat pendaftaran barang baru"
                )

            log_action(
                request.user,
                AuditLog.Action.CREATE,
                'Item',
                item.id,
                {'code': item.code, 'name': item.name, 'stock': item.stock_available},
                request=request
            )
            messages.success(request, f"Barang '{item.name}' ({item.code}) berhasil ditambahkan.")
            return redirect('inventory:item_list')
    else:
        form = ItemForm()

    return render(request, 'inventory/item_form.html', {
        'form': form,
        'title': 'Tambah Master Barang Baru',
    })


@login_required
@admin_required
def item_edit_view(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            log_action(
                request.user,
                AuditLog.Action.UPDATE,
                'Item',
                item.id,
                {'code': item.code, 'name': item.name, 'is_active': item.is_active},
                request=request
            )
            messages.success(request, f"Barang '{item.name}' berhasil diperbarui.")
            return redirect('inventory:item_list')
    else:
        form = ItemForm(instance=item)

    return render(request, 'inventory/item_form.html', {
        'form': form,
        'item': item,
        'title': f'Ubah Barang: {item.name}',
    })


@login_required
def item_detail_view(request, pk):
    item = get_object_or_404(Item.objects.select_related('category', 'location'), pk=pk)
    movements = item.movements.select_related('created_by').all()[:20]
    asset_units = item.asset_units.select_related('location').all()

    return render(request, 'inventory/item_detail.html', {
        'item': item,
        'movements': movements,
        'asset_units': asset_units,
    })


@login_required
@admin_required
def item_adjust_stock_view(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            new_available = form.cleaned_data['new_available']
            reason = form.cleaned_data['reason']
            try:
                InventoryService.adjust_stock(item.id, new_available, request.user, reason)
                messages.success(request, f"Stok tersedia '{item.name}' berhasil disesuaikan menjadi {new_available}.")
                return redirect('inventory:item_detail', pk=item.pk)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = StockAdjustmentForm(initial={'new_available': item.stock_available})

    return render(request, 'inventory/item_adjust_stock.html', {
        'form': form,
        'item': item,
    })


# --- Kategori & Lokasi ---

@login_required
@admin_required
def category_list_view(request):
    categories = Category.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
@admin_required
def category_create_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            log_action(request.user, AuditLog.Action.CREATE, 'Category', cat.id, {'name': cat.name}, request=request)
            messages.success(request, f"Kategori '{cat.name}' berhasil ditambahkan.")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()

    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Tambah Kategori Barang'})


@login_required
@admin_required
def category_edit_view(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            log_action(request.user, AuditLog.Action.UPDATE, 'Category', cat.id, {'name': cat.name}, request=request)
            messages.success(request, f"Kategori '{cat.name}' berhasil diperbarui.")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=cat)

    return render(request, 'inventory/category_form.html', {'form': form, 'title': f'Ubah Kategori: {cat.name}'})


@login_required
@admin_required
def location_list_view(request):
    locations = Location.objects.all()
    return render(request, 'inventory/location_list.html', {'locations': locations})


@login_required
@admin_required
def location_create_view(request):
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            loc = form.save()
            log_action(request.user, AuditLog.Action.CREATE, 'Location', loc.id, {'name': loc.name}, request=request)
            messages.success(request, f"Lokasi '{loc.name}' berhasil ditambahkan.")
            return redirect('inventory:location_list')
    else:
        form = LocationForm()

    return render(request, 'inventory/location_form.html', {'form': form, 'title': 'Tambah Lokasi Penyimpanan'})


@login_required
@admin_required
def location_edit_view(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=loc)
        if form.is_valid():
            form.save()
            log_action(request.user, AuditLog.Action.UPDATE, 'Location', loc.id, {'name': loc.name}, request=request)
            messages.success(request, f"Lokasi '{loc.name}' berhasil diperbarui.")
            return redirect('inventory:location_list')
    else:
        form = LocationForm(instance=loc)

    return render(request, 'inventory/location_form.html', {'form': form, 'title': f'Ubah Lokasi: {loc.name}'})


@login_required
@admin_required
def stock_ledger_view(request):
    query = request.GET.get('q', '').strip()
    movement_type = request.GET.get('movement_type', '').strip()

    movements = StockMovement.objects.select_related('item', 'created_by').all()

    if query:
        movements = movements.filter(
            Q(item__name__icontains=query) |
            Q(item__code__icontains=query) |
            Q(reference_number__icontains=query) |
            Q(reason__icontains=query)
        )
    if movement_type:
        movements = movements.filter(movement_type=movement_type)

    paginator = Paginator(movements, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/stock_ledger.html', {
        'page_obj': page_obj,
        'query': query,
        'movement_type': movement_type,
        'movement_types': StockMovement.MovementType.choices,
    })
