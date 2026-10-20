from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied

from accounts.permissions import admin_required
from inventory.models import Item, Category, StockMovement
from loans.models import LoanRequest, LoanHandover, ReturnRecord
from consumables.models import ConsumableHandover
from audit.models import AuditLog, InstitutionSetting
from .services import export_to_csv, export_to_excel, export_to_pdf


@login_required
def dashboard_dispatch_view(request):
    """
    Mengarahkan pengguna ke dashboard yang sesuai berdasarkan peran.
    """
    if request.user.is_admin_role:
        return redirect('reports:admin_dashboard')
    return redirect('reports:employee_dashboard')


@login_required
@admin_required
def admin_dashboard_view(request):
    today = timezone.now().date()

    # Hitung statistik berbasis query database nyata (bukan angka statis)
    total_items = Item.objects.filter(is_active=True).count()
    total_consumable_stock = Item.objects.filter(
        item_type=Item.ItemType.CONSUMABLE,
        is_active=True
    ).aggregate(s=Sum('stock_available'))['s'] or 0

    loanable_stats = Item.objects.filter(
        item_type=Item.ItemType.LOANABLE,
        is_active=True
    ).aggregate(
        available=Sum('stock_available'),
        loaned=Sum('stock_loaned'),
        damaged=Sum('stock_damaged'),
        lost=Sum('stock_lost')
    )

    pending_loans_count = LoanRequest.objects.filter(status=LoanRequest.Status.PENDING).count()
    active_loans_count = LoanRequest.objects.filter(
        status__in=[LoanRequest.Status.ACTIVE, LoanRequest.Status.PARTIALLY_RETURNED]
    ).count()

    overdue_loans_count = LoanRequest.objects.filter(
        status__in=[LoanRequest.Status.ACTIVE, LoanRequest.Status.PARTIALLY_RETURNED],
        due_date__lt=today
    ).count()

    consumables_period_count = ConsumableHandover.objects.filter(
        status=ConsumableHandover.Status.CONFIRMED,
        handover_date__month=today.month,
        handover_date__year=today.year
    ).count()

    # Peringatan stok minimum
    all_items = Item.objects.filter(is_active=True)
    low_stock_items = [i for i in all_items if i.is_low_stock][:8]

    # Transaksi terbaru
    recent_loans = LoanRequest.objects.select_related('borrower').order_by('-created_at')[:5]
    recent_consumables = ConsumableHandover.objects.select_related('recipient').order_by('-handover_date')[:5]

    stats = {
        'total_items': total_items,
        'consumable_stock': total_consumable_stock,
        'loanable_available': loanable_stats['available'] or 0,
        'loanable_loaned': loanable_stats['loaned'] or 0,
        'loanable_damaged': loanable_stats['damaged'] or 0,
        'loanable_lost': loanable_stats['lost'] or 0,
        'pending_loans': pending_loans_count,
        'active_loans': active_loans_count,
        'overdue_loans': overdue_loans_count,
        'consumables_month': consumables_period_count,
    }

    return render(request, 'reports/admin_dashboard.html', {
        'stats': stats,
        'low_stock_items': low_stock_items,
        'recent_loans': recent_loans,
        'recent_consumables': recent_consumables,
    })


@login_required
def employee_dashboard_view(request):
    today = timezone.now().date()
    user = request.user

    my_pending_count = LoanRequest.objects.filter(borrower=user, status=LoanRequest.Status.PENDING).count()
    my_active_loans = LoanRequest.objects.filter(
        borrower=user,
        status__in=[LoanRequest.Status.ACTIVE, LoanRequest.Status.PARTIALLY_RETURNED]
    ).prefetch_related('items__item').order_by('due_date')

    my_active_count = my_active_loans.count()
    my_overdue_count = my_active_loans.filter(due_date__lt=today).count()

    my_recent_requests = LoanRequest.objects.filter(borrower=user).prefetch_related('items__item').order_by('-created_at')[:5]

    return render(request, 'reports/employee_dashboard.html', {
        'my_pending_count': my_pending_count,
        'my_active_count': my_active_count,
        'my_overdue_count': my_overdue_count,
        'my_active_loans': my_active_loans,
        'my_recent_requests': my_recent_requests,
    })


# --- Laporan dan Rekapitulasi ---

@login_required
@admin_required
def report_index_view(request):
    return render(request, 'reports/report_index.html')


@login_required
@admin_required
def report_loans_view(request):
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status = request.GET.get('status', '')
    export_format = request.GET.get('export', '')

    loans = LoanRequest.objects.select_related('borrower', 'reviewed_by').prefetch_related('items__item').all()

    if start_date:
        loans = loans.filter(start_date__gte=start_date)
    if end_date:
        loans = loans.filter(due_date__lte=end_date)
    if status:
        loans = loans.filter(status=status)

    if export_format in ['csv', 'excel', 'pdf']:
        headers = ['No Transaksi', 'Peminjam', 'NIP', 'Unit Kerja', 'Tgl Pinjam', 'Jatuh Tempo', 'Status', 'Total Item']
        rows = []
        for l in loans:
            rows.append([
                l.loan_number,
                l.borrower.display_name,
                l.borrower.employee_number or '-',
                l.borrower.department or '-',
                f"{l.start_date:%d/%m/%Y}",
                f"{l.due_date:%d/%m/%Y}",
                l.get_status_display(),
                l.total_items_requested
            ])

        title = "Laporan Transaksi Peminjaman Barang"
        filename = f"laporan_peminjaman_{timezone.now():%Y%m%d_%H%M}"
        if export_format == 'csv':
            return export_to_csv(filename, headers, rows)
        elif export_format == 'excel':
            return export_to_excel(filename, title, headers, rows)
        elif export_format == 'pdf':
            return export_to_pdf(filename, title, headers, rows)

    paginator = Paginator(loans, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'reports/report_loans.html', {
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'statuses': LoanRequest.Status.choices,
    })


@login_required
@admin_required
def report_returns_view(request):
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    export_format = request.GET.get('export', '')

    returns = ReturnRecord.objects.select_related('loan__borrower', 'received_by').prefetch_related('items__loan_item__item').all()

    if start_date:
        returns = returns.filter(return_date__date__gte=start_date)
    if end_date:
        returns = returns.filter(return_date__date__lte=end_date)

    if export_format in ['csv', 'excel', 'pdf']:
        headers = ['No Pengembalian', 'No Pinjam', 'Peminjam', 'Waktu Kembali', 'Petugas Penerima', 'Catatan']
        rows = []
        for r in returns:
            rows.append([
                r.return_number,
                r.loan.loan_number,
                r.loan.borrower.display_name,
                f"{r.return_date:%d/%m/%Y %H:%M}",
                r.received_by.display_name,
                r.notes or '-'
            ])

        title = "Laporan Pengembalian Barang Pinjaman"
        filename = f"laporan_pengembalian_{timezone.now():%Y%m%d_%H%M}"
        if export_format == 'csv':
            return export_to_csv(filename, headers, rows)
        elif export_format == 'excel':
            return export_to_excel(filename, title, headers, rows)
        elif export_format == 'pdf':
            return export_to_pdf(filename, title, headers, rows)

    paginator = Paginator(returns, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'reports/report_returns.html', {
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
@admin_required
def report_consumables_view(request):
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    department = request.GET.get('department', '').strip()
    export_format = request.GET.get('export', '')

    handovers = ConsumableHandover.objects.select_related('recipient', 'created_by').prefetch_related('items__item').all()

    if start_date:
        handovers = handovers.filter(handover_date__date__gte=start_date)
    if end_date:
        handovers = handovers.filter(handover_date__date__lte=end_date)
    if department:
        handovers = handovers.filter(department__icontains=department)

    if export_format in ['csv', 'excel', 'pdf']:
        headers = ['No Penyerahan', 'Penerima', 'Unit Kerja', 'Waktu Serah', 'Tujuan Dinas', 'Status', 'Total Unit']
        rows = []
        for h in handovers:
            rows.append([
                h.handover_number,
                h.recipient.display_name,
                h.department or '-',
                f"{h.handover_date:%d/%m/%Y %H:%M}",
                h.purpose,
                h.get_status_display(),
                h.total_quantity
            ])

        title = "Laporan Penyerahan Barang Habis Pakai"
        filename = f"laporan_habis_pakai_{timezone.now():%Y%m%d_%H%M}"
        if export_format == 'csv':
            return export_to_csv(filename, headers, rows)
        elif export_format == 'excel':
            return export_to_excel(filename, title, headers, rows)
        elif export_format == 'pdf':
            return export_to_pdf(filename, title, headers, rows)

    paginator = Paginator(handovers, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'reports/report_consumables.html', {
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'department': department,
    })


@login_required
@admin_required
def report_stock_view(request):
    item_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    low_stock = request.GET.get('low_stock', '')
    export_format = request.GET.get('export', '')

    items = Item.objects.select_related('category', 'location').all()

    if item_type:
        items = items.filter(item_type=item_type)
    if category_id:
        items = items.filter(category_id=category_id)
    if low_stock == '1':
        items = [i for i in items if i.is_low_stock]

    if export_format in ['csv', 'excel', 'pdf']:
        headers = ['Kode', 'Nama Barang', 'Kategori', 'Tipe', 'Satuan', 'Tersedia', 'Dipinjam', 'Rusak', 'Hilang', 'Total Fisik']
        rows = []
        for item in items:
            rows.append([
                item.code,
                item.name,
                item.category.name,
                item.get_item_type_display(),
                item.unit,
                item.stock_available,
                item.stock_loaned,
                item.stock_damaged,
                item.stock_lost,
                item.total_stock
            ])

        title = "Laporan Rekapitulasi Stok Inventaris"
        filename = f"laporan_stok_inventaris_{timezone.now():%Y%m%d_%H%M}"
        if export_format == 'csv':
            return export_to_csv(filename, headers, rows)
        elif export_format == 'excel':
            return export_to_excel(filename, title, headers, rows)
        elif export_format == 'pdf':
            return export_to_pdf(filename, title, headers, rows)

    paginator = Paginator(items, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = Category.objects.filter(is_active=True)

    return render(request, 'reports/report_stock.html', {
        'page_obj': page_obj,
        'categories': categories,
        'item_types': Item.ItemType.choices,
        'selected_type': item_type,
        'selected_category': category_id,
        'selected_low_stock': low_stock,
    })


# --- Cetak Slip Bukti Transaksi Resmi (Printable CSS Slip) ---

@login_required
def print_loan_slip_view(request, pk):
    loan = get_object_or_404(
        LoanRequest.objects.select_related('borrower', 'reviewed_by').prefetch_related('items__item'),
        pk=pk
    )
    if not request.user.is_admin_role and loan.borrower != request.user:
        raise PermissionDenied("Akses ditolak.")

    setting = InstitutionSetting.objects.first()
    return render(request, 'reports/slips/loan_slip.html', {
        'loan': loan,
        'setting': setting,
    })


@login_required
def print_handover_slip_view(request, pk):
    handover = get_object_or_404(
        LoanHandover.objects.select_related('loan__borrower', 'handed_over_by', 'recipient').prefetch_related('items__loan_item__item'),
        pk=pk
    )
    if not request.user.is_admin_role and handover.recipient != request.user:
        raise PermissionDenied("Akses ditolak.")

    setting = InstitutionSetting.objects.first()
    return render(request, 'reports/slips/handover_slip.html', {
        'handover': handover,
        'setting': setting,
    })


@login_required
def print_return_slip_view(request, pk):
    return_rec = get_object_or_404(
        ReturnRecord.objects.select_related('loan__borrower', 'received_by').prefetch_related('items__loan_item__item'),
        pk=pk
    )
    if not request.user.is_admin_role and return_rec.loan.borrower != request.user:
        raise PermissionDenied("Akses ditolak.")

    setting = InstitutionSetting.objects.first()
    return render(request, 'reports/slips/return_slip.html', {
        'return_rec': return_rec,
        'setting': setting,
    })


@login_required
def print_consumable_slip_view(request, pk):
    handover = get_object_or_404(
        ConsumableHandover.objects.select_related('recipient', 'created_by').prefetch_related('items__item'),
        pk=pk
    )
    if not request.user.is_admin_role and handover.recipient != request.user:
        raise PermissionDenied("Akses ditolak.")

    setting = InstitutionSetting.objects.first()
    return render(request, 'reports/slips/consumable_slip.html', {
        'handover': handover,
        'setting': setting,
    })
