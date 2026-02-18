from django.urls import path
from . import views

urlpatterns = [
    path('',                                views.user_list_view, name='user_list'),
    path('register/',                       views.register_view,  name='register'),
    path('login/',                          views.login_view,     name='login'),
    path('logout/',                         views.logout_view,    name='logout'),
    path('chat/<int:user_id>/',             views.chat_view,      name='chat'),
    path('delete-message/<int:message_id>/', views.delete_message, name='delete_message'),
    path('unread-counts/', views.unread_counts, name='unread_counts'),
]