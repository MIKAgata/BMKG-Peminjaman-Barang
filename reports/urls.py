from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboards
    path('', views.dashboard_dispatch_view, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('my-dashboard/', views.employee_dashboard_view, name='employee_dashboard'),

    # Laporan
    path('laporan/', views.report_index_view, name='report_index'),
    path('laporan/peminjaman/', views.report_loans_view, name='report_loans'),
    path('laporan/pengembalian/', views.report_returns_view, name='report_returns'),
    path('laporan/habis-pakai/', views.report_consumables_view, name='report_consumables'),
    path('laporan/stok/', views.report_stock_view, name='report_stock'),

    # Bukti Cetak Transaksi (Printable Slips)
    path('print/loan/<int:pk>/', views.print_loan_slip_view, name='print_loan_slip'),
    path('print/handover/<int:pk>/', views.print_handover_slip_view, name='print_handover_slip'),
    path('print/return/<int:pk>/', views.print_return_slip_view, name='print_return_slip'),
    path('print/consumable/<int:pk>/', views.print_consumable_slip_view, name='print_consumable_slip'),
]
