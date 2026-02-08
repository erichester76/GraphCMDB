# cmdb/api/urls.py
"""
URL configuration for GraphCMDB REST API.
Uses Django REST Framework routers for ViewSet-based endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import NodeTypeViewSet, NodeViewSet

app_name = 'api'

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'types', NodeTypeViewSet, basename='node-type')

# Custom URL patterns for node operations with label parameter
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Node CRUD operations (ViewSet actions)
    path('nodes/<str:label>/', NodeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='node-list'),
    
    path('nodes/<str:label>/<str:pk>/', NodeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='node-detail'),
    
    # Relationship operations
    path('nodes/<str:label>/<str:pk>/relationships/', NodeViewSet.as_view({
        'post': 'relationships'
    }), name='node-relationships'),
    
    path('nodes/<str:label>/<str:pk>/relationships/<str:relationship_type>/<str:target_id>/', 
         NodeViewSet.as_view({
             'delete': 'disconnect'
         }), name='node-disconnect'),
]
