from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('logs/', views.audit_log_list_view, name='log_list'),
    path('settings/', views.setting_view, name='setting_view'),
]
