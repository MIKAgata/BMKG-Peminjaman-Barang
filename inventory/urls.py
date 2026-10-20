from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Master Barang
    path('items/', views.item_list_view, name='item_list'),
    path('items/create/', views.item_create_view, name='item_create'),
    path('items/<int:pk>/', views.item_detail_view, name='item_detail'),
    path('items/<int:pk>/edit/', views.item_edit_view, name='item_edit'),
    path('items/<int:pk>/adjust-stock/', views.item_adjust_stock_view, name='item_adjust_stock'),

    # Kategori
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/create/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit_view, name='category_edit'),

    # Lokasi
    path('locations/', views.location_list_view, name='location_list'),
    path('locations/create/', views.location_create_view, name='location_create'),
    path('locations/<int:pk>/edit/', views.location_edit_view, name='location_edit'),

    # Stock Movement Ledger
    path('ledger/', views.stock_ledger_view, name='stock_ledger'),
]
