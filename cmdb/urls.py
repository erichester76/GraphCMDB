# cmdb/urls.py
from django.urls import path, include
from . import views
from . import feature_pack_views

app_name = 'cmdb'  

urlpatterns = [
        path('', views.dashboard, name='dashboard'),
    
    path('', include('cmdb.feature_pack_urls')),
    
    path('targets/', views.get_target_nodes, name='get_target_nodes'),
    
    # Feature pack management URLs
    path('feature-packs/', feature_pack_views.feature_pack_list, name='feature_pack_list'),
    path('feature-packs/api/status/', feature_pack_views.feature_pack_status_api, name='feature_pack_status_api'),
    path('feature-packs/add/', feature_pack_views.feature_pack_add, name='feature_pack_add'),
    path('feature-packs/refresh-store/', feature_pack_views.feature_pack_refresh_store, name='feature_pack_refresh_store'),
    path('feature-packs/<str:pack_name>/', feature_pack_views.feature_pack_detail, name='feature_pack_detail'),
    path('feature-packs/store/<str:pack_name>/', feature_pack_views.feature_pack_store_detail, name='feature_pack_store_detail'),
    path('feature-packs/<str:pack_name>/enable/', feature_pack_views.feature_pack_enable, name='feature_pack_enable'),
    path('feature-packs/<str:pack_name>/disable/', feature_pack_views.feature_pack_disable, name='feature_pack_disable'),
    path('feature-packs/<str:pack_name>/delete/', feature_pack_views.feature_pack_delete, name='feature_pack_delete'),

    path('setup/', views.first_time_wizard, name='first_time_wizard'),

    path('<str:label>/', views.nodes_list, name='nodes_list'),
    path('<str:label>/create/', views.node_create, name='node_create'),
    path('<str:label>/import/', views.node_import, name='node_import'),
    path('<str:label>/<str:element_id>/', views.node_detail, name='node_detail'),
    path('<str:label>/<str:element_id>/edit/', views.node_edit, name='node_edit'),
    path('<str:label>/<str:element_id>/delete/', views.node_delete, name='node_delete'),
    path('<str:label>/<str:element_id>/connect/', views.node_connect, name='node_connect'),
    path('<str:label>/<str:element_id>/disconnect/', views.node_disconnect, name='node_disconnect'),
    path('<str:label>/<str:element_id>/add-relationship-form/', views.node_add_relationship_form, name='node_add_relationship_form'),
    
 
]