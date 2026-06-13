from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/<int:session_id>/send/', views.send_message, name='send_message'),
    path('session/<int:session_id>/toggle-highlight/', views.toggle_highlight, name='toggle_highlight'),
    path('session/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('session/<int:session_id>/rename/', views.rename_session, name='rename_session'),
    path('session/new/', views.new_session, name='new_session'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/save/', views.save_settings, name='save_settings'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
]