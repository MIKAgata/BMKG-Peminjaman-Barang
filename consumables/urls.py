from django.urls import path
from . import views

app_name = 'consumables'

urlpatterns = [
    path('', views.handover_list_view, name='handover_list'),
    path('create/', views.handover_create_view, name='handover_create'),
    path('<int:pk>/', views.handover_detail_view, name='handover_detail'),
    path('<int:pk>/cancel/', views.handover_cancel_view, name='handover_cancel'),
]
