from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # Pegawai
    path('catalog/', views.catalog_view, name='catalog'),
    path('apply/', views.loan_apply_view, name='loan_apply'),
    path('my-loans/', views.my_loans_view, name='my_loans'),
    path('<int:pk>/', views.loan_detail_view, name='loan_detail'),
    path('<int:pk>/cancel/', views.loan_cancel_view, name='loan_cancel'),

    # Admin Peminjaman
    path('requests/', views.loan_request_list_view, name='loan_request_list'),
    path('<int:pk>/review/', views.loan_review_view, name='loan_review'),

    # Serah Terima Fisik
    path('handovers/', views.handover_list_view, name='handover_list'),
    path('<int:loan_pk>/handover/', views.handover_create_view, name='handover_create'),

    # Pengembalian
    path('returns/', views.return_list_view, name='return_list'),
    path('<int:loan_pk>/return/', views.return_create_view, name='return_create'),
]
