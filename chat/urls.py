from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/perguntar/', views.perguntar, name='perguntar'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/save/', views.save_settings, name='save_settings'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
]