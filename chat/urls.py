from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('chat/', views.index, name='index'),
    path('logout/', views.logout_page, name='logout'),
    path('chat/perguntar/', views.perguntar, name='perguntar'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/save/', views.save_settings, name='save_settings'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
]