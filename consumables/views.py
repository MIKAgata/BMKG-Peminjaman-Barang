from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ValidationError

from accounts.permissions import admin_required
from inventory.models import Item, StockMovement
from inventory.services import InventoryService
from .models import ConsumableHandover, ConsumableHandoverItem
from .forms import ConsumableHandoverForm, ConsumableItemFormSet
from audit.utils import log_action
from audit.models import AuditLog


@login_required
@admin_required
def handover_list_view(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    handovers = ConsumableHandover.objects.select_related('recipient', 'created_by').prefetch_related('items__item').all()

    if status_filter:
        handovers = handovers.filter(status=status_filter)
    if query:
        handovers = handovers.filter(
            Q(handover_number__icontains=query) |
            Q(recipient__username__icontains=query) |
            Q(recipient__first_name__icontains=query) |
            Q(recipient__last_name__icontains=query) |
            Q(department__icontains=query) |
            Q(purpose__icontains=query)
        )

    paginator = Paginator(handovers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'consumables/handover_list.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'statuses': ConsumableHandover.Status.choices,
    })


@login_required
@admin_required
def handover_create_view(request):
    """
    Pencatatan penyerahan barang habis pakai (CONSUMABLE).
    Stok berkurang secara atomik setelah transaksi dikonfirmasi.
    """
    if request.method == 'POST':
        form = ConsumableHandoverForm(request.POST)
        formset = ConsumableItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                handover = form.save(commit=False)
                handover.created_by = request.user
                handover.status = ConsumableHandover.Status.CONFIRMED
                # Set default department from recipient if empty
                if not handover.department and handover.recipient.department:
                    handover.department = handover.recipient.department
                handover.save()

                items_saved = 0
                for item_form in formset:
                    if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE'):
                        c_item = item_form.save(commit=False)
                        c_item.handover = handover

                        # Validasi tipe CONSUMABLE
                        if c_item.item.item_type != Item.ItemType.CONSUMABLE:
                            messages.error(request, f"Barang '{c_item.item.name}' bukan barang habis pakai!")
                            transaction.set_rollback(True)
                            return render(request, 'consumables/handover_form.html', {'form': form, 'formset': formset})

                        # Deduct stock via service
                        try:
                            InventoryService.issue_consumable(
                                item_id=c_item.item.id,
                                quantity=c_item.quantity,
                                reference_number=handover.handover_number,
                                user=request.user,
                                reason=f"Penyerahan barang habis pakai {handover.handover_number} kepada {handover.recipient.display_name}"
                            )
                        except ValidationError as e:
                            messages.error(request, str(e.message if hasattr(e, 'message') else e))
                            transaction.set_rollback(True)
                            return render(request, 'consumables/handover_form.html', {'form': form, 'formset': formset})

                        c_item.save()
                        items_saved += 1

                if items_saved == 0:
                    messages.error(request, "Pilih minimal satu barang habis pakai untuk diserahkan.")
                    transaction.set_rollback(True)
                    return render(request, 'consumables/handover_form.html', {'form': form, 'formset': formset})

                messages.success(request, f"Penyerahan barang habis pakai ({handover.handover_number}) berhasil disimpan dan stok gudang terpotong.")
                return redirect('consumables:handover_detail', pk=handover.pk)
    else:
        form = ConsumableHandoverForm()
        formset = ConsumableItemFormSet()

    return render(request, 'consumables/handover_form.html', {
        'form': form,
        'formset': formset,
    })


@login_required
def handover_detail_view(request, pk):
    handover = get_object_or_404(
        ConsumableHandover.objects.select_related('recipient', 'created_by').prefetch_related('items__item'),
        pk=pk
    )

    if not request.user.is_admin_role and handover.recipient != request.user:
        raise PermissionDenied("Anda tidak memiliki akses untuk melihat transaksi ini.")

    return render(request, 'consumables/handover_detail.html', {
        'handover': handover,
    })


@login_required
@admin_required
def handover_cancel_view(request, pk):
    """
    Pembatalan penyerahan barang habis pakai oleh Admin.
    Stok dikembalikan ke gudang secara atomik dengan reversing StockMovement.
    """
    handover = get_object_or_404(ConsumableHandover.objects.prefetch_related('items__item'), pk=pk)

    if handover.status == ConsumableHandover.Status.CANCELLED:
        messages.warning(request, "Transaksi ini sudah dibatalkan sebelumnya.")
        return redirect('consumables:handover_detail', pk=handover.pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Alasan pembatalan wajib diisi.")
            return render(request, 'consumables/handover_cancel.html', {'handover': handover})

        with transaction.atomic():
            handover.status = ConsumableHandover.Status.CANCELLED
            handover.cancellation_reason = reason
            handover.save()

            # Reverse stock for each item
            for c_item in handover.items.all():
                item = Item.objects.select_for_update().get(pk=c_item.item.pk)
                avail_before = item.stock_available
                item.stock_available += c_item.quantity
                item.save()

                StockMovement.objects.create(
                    item=item,
                    movement_type=StockMovement.MovementType.CANCELLATION,
                    quantity=c_item.quantity,
                    stock_available_before=avail_before,
                    stock_available_after=item.stock_available,
                    stock_loaned_before=0,
                    stock_loaned_after=0,
                    reference_number=f"BATAL-{handover.handover_number}",
                    created_by=request.user,
                    reason=f"Pembatalan transaksi penyerahan {handover.handover_number}: {reason}"
                )

            log_action(
                request.user,
                AuditLog.Action.CANCEL,
                'ConsumableHandover',
                handover.id,
                {'reason': reason},
                request=request
            )
            messages.info(request, f"Transaksi ({handover.handover_number}) berhasil dibatalkan dan stok dikembalikan.")
            return redirect('consumables:handover_detail', pk=handover.pk)

    return render(request, 'consumables/handover_cancel.html', {
        'handover': handover,
    })
