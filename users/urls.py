from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='profile'),
    path('list/', views.user_list, name='user_list'),
    path('groups/', views.group_list, name='group_list'),
]
