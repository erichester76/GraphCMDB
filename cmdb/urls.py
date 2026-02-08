# cmdb/urls.py
from django.urls import path
from . import views

app_name = 'cmdb'  

urlpatterns = [
    path('types/register/', views.type_register, name='type_register'),
    
    path('', views.dashboard, name='dashboard'),
    
    path('audit-log/', views.audit_log_list, name='audit_log_list'),
    
    path('targets/', views.get_target_nodes, name='get_target_nodes'),

    path('<str:label>/', views.nodes_list, name='nodes_list'),
    path('<str:label>/create/', views.node_create, name='node_create'),
    path('<str:label>/<str:element_id>/', views.node_detail, name='node_detail'),
    path('<str:label>/<str:element_id>/edit/', views.node_edit, name='node_edit'),
    path('<str:label>/<str:element_id>/delete/', views.node_delete, name='node_delete'),
    path('<str:label>/<str:element_id>/connect/', views.node_connect, name='node_connect'),
    path('<str:label>/<str:element_id>/disconnect/', views.node_disconnect, name='node_disconnect'),
    path('<str:label>/<str:element_id>/add-relationship-form/', views.node_add_relationship_form, name='node_add_relationship_form'),
    
 
]