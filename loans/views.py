from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError

from accounts.permissions import admin_required
from inventory.models import Item
from inventory.services import InventoryService
from .models import LoanRequest, LoanItem, LoanHandover, LoanHandoverItem, ReturnRecord, ReturnItem
from .forms import LoanApplyForm, LoanItemFormSet, LoanReviewForm, LoanCancelForm
from audit.utils import log_action
from audit.models import AuditLog


@login_required
def catalog_view(request):
    """
    Katalog barang pinjaman (LOANABLE) yang tersedia untuk pegawai.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()

    items = Item.objects.filter(
        item_type=Item.ItemType.LOANABLE,
        is_active=True
    ).select_related('category', 'location')

    if query:
        items = items.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(brand__icontains=query)
        )
    if category_id:
        items = items.filter(category_id=category_id)

    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from inventory.models import Category
    categories = Category.objects.filter(is_active=True)

    return render(request, 'loans/catalog.html', {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
    })


@login_required
def loan_apply_view(request):
    """
    Formulir pengajuan peminjaman barang oleh pegawai.
    Pengajuan TIDAK mengurangi stok gudang.
    """
    if request.method == 'POST':
        form = LoanApplyForm(request.POST)
        formset = LoanItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                loan = form.save(commit=False)
                loan.borrower = request.user
                loan.status = LoanRequest.Status.PENDING
                loan.save()

                items_saved = 0
                for item_form in formset:
                    if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE'):
                        loan_item = item_form.save(commit=False)
                        loan_item.loan = loan

                        # Validasi tipe LOANABLE
                        if loan_item.item.item_type != Item.ItemType.LOANABLE:
                            messages.error(request, f"Barang '{loan_item.item.name}' tidak dapat dipinjam.")
                            transaction.set_rollback(True)
                            return render(request, 'loans/loan_apply.html', {'form': form, 'formset': formset})

                        loan_item.save()
                        items_saved += 1

                if items_saved == 0:
                    messages.error(request, "Pilih minimal satu barang untuk dipinjam.")
                    transaction.set_rollback(True)
                    return render(request, 'loans/loan_apply.html', {'form': form, 'formset': formset})

                log_action(
                    request.user,
                    AuditLog.Action.CREATE,
                    'LoanRequest',
                    loan.id,
                    {'loan_number': loan.loan_number, 'purpose': loan.purpose},
                    request=request
                )

                messages.success(request, f"Pengajuan peminjaman ({loan.loan_number}) berhasil diajukan dan menunggu persetujuan.")
                return redirect('loans:loan_detail', pk=loan.pk)
    else:
        form = LoanApplyForm()
        formset = LoanItemFormSet()

    return render(request, 'loans/loan_apply.html', {
        'form': form,
        'formset': formset,
    })


@login_required
def my_loans_view(request):
    """
    Daftar pengajuan dan riwayat peminjaman milik pegawai yang sedang login.
    """
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    loans = LoanRequest.objects.filter(borrower=request.user).prefetch_related('items__item')

    if status_filter:
        loans = loans.filter(status=status_filter)
    if query:
        loans = loans.filter(
            Q(loan_number__icontains=query) |
            Q(purpose__icontains=query)
        )

    paginator = Paginator(loans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'loans/my_loans.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'query': query,
        'statuses': LoanRequest.Status.choices,
    })


@login_required
def loan_detail_view(request, pk):
    """
    Detail transaksi peminjaman.
    Pegawai hanya boleh melihat peminjaman miliknya sendiri. Admin dapat melihat semua.
    """
    loan = get_object_or_404(
        LoanRequest.objects.select_related('borrower', 'reviewed_by').prefetch_related(
            'items__item', 'handovers__items__loan_item__item', 'returns__items__loan_item__item'
        ),
        pk=pk
    )

    if not request.user.is_admin_role and loan.borrower != request.user:
        raise PermissionDenied("Anda tidak berhak melihat transaksi peminjaman pegawai lain.")

    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
    })


# --- Admin Loan Operations ---

@login_required
@admin_required
def loan_request_list_view(request):
    """
    Daftar seluruh pengajuan peminjaman untuk admin.
    """
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    loans = LoanRequest.objects.select_related('borrower').prefetch_related('items__item').all()

    if status_filter:
        loans = loans.filter(status=status_filter)
    if query:
        loans = loans.filter(
            Q(loan_number__icontains=query) |
            Q(borrower__first_name__icontains=query) |
            Q(borrower__last_name__icontains=query) |
            Q(borrower__username__icontains=query) |
            Q(purpose__icontains=query)
        )

    paginator = Paginator(loans, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'loans/loan_request_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'query': query,
        'statuses': LoanRequest.Status.choices,
    })


@login_required
@admin_required
def loan_review_view(request, pk):
    """
    Admin menyetujui (APPROVED) atau menolak (REJECTED) pengajuan.
    Persetujuan TIDAK mengurangi stok gudang sampai serah terima fisik dilakukan.
    """
    loan = get_object_or_404(LoanRequest, pk=pk)

    if loan.status != LoanRequest.Status.PENDING:
        messages.warning(request, f"Peminjaman ({loan.loan_number}) sudah diproses sebelumnya (Status: {loan.get_status_display()}).")
        return redirect('loans:loan_detail', pk=loan.pk)

    if request.method == 'POST':
        form = LoanReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            reason = form.cleaned_data.get('rejection_reason', '')

            if action == 'APPROVE':
                loan.status = LoanRequest.Status.APPROVED
                loan.reviewed_by = request.user
                loan.reviewed_at = timezone.now()
                loan.save()
                log_action(
                    request.user,
                    AuditLog.Action.APPROVE,
                    'LoanRequest',
                    loan.id,
                    {'status': 'APPROVED'},
                    request=request
                )
                messages.success(request, f"Pengajuan ({loan.loan_number}) berhasil DISETUJUI. Lanjutkan ke Serah Terima Fisik saat barang diambil.")
            elif action == 'REJECT':
                loan.status = LoanRequest.Status.REJECTED
                loan.reviewed_by = request.user
                loan.reviewed_at = timezone.now()
                loan.rejection_reason = reason
                loan.save()
                log_action(
                    request.user,
                    AuditLog.Action.REJECT,
                    'LoanRequest',
                    loan.id,
                    {'status': 'REJECTED', 'reason': reason},
                    request=request
                )
                messages.warning(request, f"Pengajuan ({loan.loan_number}) DITOLAK.")

            return redirect('loans:loan_detail', pk=loan.pk)
    else:
        form = LoanReviewForm()

    return render(request, 'loans/loan_review.html', {
        'loan': loan,
        'form': form,
    })


@login_required
def loan_cancel_view(request, pk):
    """
    Pembatalan peminjaman.
    Hanya peminjaman berstatus PENDING atau APPROVED (sebelum serah terima) yang dapat dibatalkan.
    """
    loan = get_object_or_404(LoanRequest, pk=pk)

    if not request.user.is_admin_role and loan.borrower != request.user:
        raise PermissionDenied("Akses ditolak.")

    if loan.status not in [LoanRequest.Status.PENDING, LoanRequest.Status.APPROVED]:
        messages.error(request, "Peminjaman yang barangnya sudah diserahkan fisik tidak dapat dibatalkan melalui menu ini.")
        return redirect('loans:loan_detail', pk=loan.pk)

    if request.method == 'POST':
        form = LoanCancelForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            loan.status = LoanRequest.Status.CANCELLED
            loan.cancellation_reason = reason
            loan.save()

            log_action(
                request.user,
                AuditLog.Action.CANCEL,
                'LoanRequest',
                loan.id,
                {'reason': reason},
                request=request
            )
            messages.info(request, f"Peminjaman ({loan.loan_number}) berhasil dibatalkan.")
            return redirect('loans:loan_detail', pk=loan.pk)
    else:
        form = LoanCancelForm()

    return render(request, 'loans/loan_cancel.html', {
        'loan': loan,
        'form': form,
    })


# --- Serah Terima Fisik Barang Pinjaman ---

@login_required
@admin_required
def handover_list_view(request):
    handovers = LoanHandover.objects.select_related('loan', 'handed_over_by', 'recipient').prefetch_related('items__loan_item__item').all()
    paginator = Paginator(handovers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'loans/handover_list.html', {
        'page_obj': page_obj,
    })


@login_required
@admin_required
def handover_create_view(request, loan_pk):
    """
    Pencatatan penyerahan fisik barang pinjaman.
    STOK TERSEDIA BERKURANG HANYA PADA LANGKAH INI!
    """
    loan = get_object_or_404(LoanRequest.objects.prefetch_related('items__item'), pk=loan_pk)

    if loan.status not in [LoanRequest.Status.APPROVED, LoanRequest.Status.ACTIVE, LoanRequest.Status.PARTIALLY_RETURNED]:
        messages.error(request, f"Tidak dapat melakukan serah terima untuk status '{loan.get_status_display()}'.")
        return redirect('loans:loan_detail', pk=loan.pk)

    # Filter items that still have pending items to hand over
    pending_items = [item for item in loan.items.all() if item.quantity_remaining_to_handover > 0]
    if not pending_items:
        messages.info(request, "Semua barang untuk peminjaman ini telah diserahkan.")
        return redirect('loans:loan_detail', pk=loan.pk)

    if request.method == 'POST':
        with transaction.atomic():
            handover = LoanHandover.objects.create(
                loan=loan,
                handed_over_by=request.user,
                recipient=loan.borrower,
                notes=request.POST.get('notes', '').strip()
            )

            total_handed = 0
            for l_item in pending_items:
                field_name = f"qty_{l_item.id}"
                qty_str = request.POST.get(field_name, '0').strip()
                try:
                    qty = int(qty_str)
                except ValueError:
                    qty = 0

                if qty > 0:
                    if qty > l_item.quantity_remaining_to_handover:
                        messages.error(
                            request,
                            f"Jumlah serah terima {l_item.item.name} ({qty}) melebihi sisa yang diajukan ({l_item.quantity_remaining_to_handover})."
                        )
                        transaction.set_rollback(True)
                        return redirect('loans:handover_create', loan_pk=loan.pk)

                    # Deduct from inventory atomically via service
                    try:
                        InventoryService.issue_loan(
                            item_id=l_item.item.id,
                            quantity=qty,
                            reference_number=handover.handover_number,
                            user=request.user,
                            reason=f"Serah terima pinjaman {loan.loan_number}"
                        )
                    except ValidationError as e:
                        messages.error(request, str(e.message if hasattr(e, 'message') else e))
                        transaction.set_rollback(True)
                        return redirect('loans:handover_create', loan_pk=loan.pk)

                    # Record handover item
                    LoanHandoverItem.objects.create(
                        handover=handover,
                        loan_item=l_item,
                        quantity=qty,
                        initial_condition=request.POST.get(f"cond_{l_item.id}", "Baik / Layak Pakai")
                    )

                    l_item.quantity_handed_over += qty
                    l_item.save()
                    total_handed += qty

            if total_handed == 0:
                messages.error(request, "Masukkan minimal 1 unit barang yang diserahkan fisik.")
                transaction.set_rollback(True)
                return redirect('loans:handover_create', loan_pk=loan.pk)

            # Update loan status to ACTIVE if not partially returned
            if loan.status != LoanRequest.Status.PARTIALLY_RETURNED:
                loan.status = LoanRequest.Status.ACTIVE
                loan.save()

            messages.success(request, f"Serah terima fisik ({handover.handover_number}) berhasil dicatat. Stok gudang telah dipotong.")
            return redirect('loans:loan_detail', pk=loan.pk)

    return render(request, 'loans/handover_form.html', {
        'loan': loan,
        'pending_items': pending_items,
    })


# --- Pengembalian Barang Pinjaman ---

@login_required
@admin_required
def return_list_view(request):
    returns = ReturnRecord.objects.select_related('loan', 'received_by').prefetch_related('items__loan_item__item').all()
    paginator = Paginator(returns, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'loans/return_list.html', {
        'page_obj': page_obj,
    })


@login_required
@admin_required
def return_create_view(request, loan_pk):
    """
    Pencatatan pengembalian barang pinjaman.
    Mendukung pengembalian penuh atau sebagian.
    Stok tersedia bertambah HANYA untuk barang layak pakai.
    """
    loan = get_object_or_404(LoanRequest.objects.prefetch_related('items__item'), pk=loan_pk)

    if loan.status not in [LoanRequest.Status.ACTIVE, LoanRequest.Status.PARTIALLY_RETURNED]:
        messages.error(request, f"Peminjaman dengan status '{loan.get_status_display()}' tidak dapat diproses pengembalian.")
        return redirect('loans:loan_detail', pk=loan.pk)

    items_to_return = [item for item in loan.items.all() if item.quantity_remaining_to_return > 0]
    if not items_to_return:
        messages.info(request, "Semua barang peminjaman ini telah dikembalikan.")
        return redirect('loans:loan_detail', pk=loan.pk)

    if request.method == 'POST':
        with transaction.atomic():
            return_record = ReturnRecord.objects.create(
                loan=loan,
                received_by=request.user,
                notes=request.POST.get('notes', '').strip()
            )

            total_returned_now = 0
            for l_item in items_to_return:
                usable = int(request.POST.get(f"usable_{l_item.id}", 0) or 0)
                damaged = int(request.POST.get(f"damaged_{l_item.id}", 0) or 0)
                lost = int(request.POST.get(f"lost_{l_item.id}", 0) or 0)
                subtotal = usable + damaged + lost

                if subtotal > 0:
                    if subtotal > l_item.quantity_remaining_to_return:
                        messages.error(
                            request,
                            f"Total pengembalian {l_item.item.name} ({subtotal}) melebihi jumlah yang belum kembali ({l_item.quantity_remaining_to_return})."
                        )
                        transaction.set_rollback(True)
                        return redirect('loans:return_create', loan_pk=loan.pk)

                    # Update stock via service
                    try:
                        InventoryService.return_loan_items(
                            item_id=l_item.item.id,
                            qty_usable=usable,
                            qty_damaged=damaged,
                            qty_lost=lost,
                            reference_number=return_record.return_number,
                            user=request.user,
                            reason=f"Pengembalian pinjaman {loan.loan_number}"
                        )
                    except ValidationError as e:
                        messages.error(request, str(e))
                        transaction.set_rollback(True)
                        return redirect('loans:return_create', loan_pk=loan.pk)

                    # Save ReturnItem
                    ReturnItem.objects.create(
                        return_record=return_record,
                        loan_item=l_item,
                        quantity_usable=usable,
                        quantity_damaged=damaged,
                        quantity_lost=lost,
                        damage_notes=request.POST.get(f"notes_{l_item.id}", '').strip()
                    )

                    l_item.quantity_returned_usable += usable
                    l_item.quantity_returned_damaged += damaged
                    l_item.quantity_returned_lost += lost
                    l_item.save()
                    total_returned_now += subtotal

            if total_returned_now == 0:
                messages.error(request, "Masukkan minimal 1 unit barang yang dikembalikan.")
                transaction.set_rollback(True)
                return redirect('loans:return_create', loan_pk=loan.pk)

            # Check if all items are fully returned
            all_returned = all(item.quantity_remaining_to_return == 0 for item in loan.items.all())
            if all_returned:
                loan.status = LoanRequest.Status.COMPLETED
            else:
                loan.status = LoanRequest.Status.PARTIALLY_RETURNED
            loan.save()

            messages.success(
                request,
                f"Pengembalian ({return_record.return_number}) berhasil dicatat. Status pinjaman kini: {loan.get_status_display()}."
            )
            return redirect('loans:loan_detail', pk=loan.pk)

    return render(request, 'loans/return_form.html', {
        'loan': loan,
        'items_to_return': items_to_return,
    })
