# cmdb/api_urls.py
"""
URL patterns for REST API endpoints.
All endpoints return JSON responses.
"""
from django.urls import path
from . import api

app_name = 'api'

urlpatterns = [
    # List all node types
    path('types/', api.api_list_node_types, name='list_node_types'),
    
    # CRUD operations for nodes
    path('nodes/<str:label>/', api.api_list_nodes, name='list_nodes'),
    path('nodes/<str:label>/create/', api.api_create_node, name='create_node'),
    path('nodes/<str:label>/<str:element_id>/', api.api_get_node, name='get_node'),
    path('nodes/<str:label>/<str:element_id>/update/', api.api_update_node, name='update_node'),
    path('nodes/<str:label>/<str:element_id>/delete/', api.api_delete_node, name='delete_node'),
    
    # Relationship operations
    path('nodes/<str:label>/<str:element_id>/relationships/', api.api_connect_nodes, name='connect_nodes'),
    path('nodes/<str:label>/<str:element_id>/relationships/<str:relationship_type>/<str:target_id>/', 
         api.api_disconnect_nodes, name='disconnect_nodes'),
]
