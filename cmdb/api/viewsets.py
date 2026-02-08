# cmdb/api/viewsets.py
"""
ViewSets for GraphCMDB REST API.
Provides CRUD operations for all node types using Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from neomodel import db

from cmdb.models import DynamicNode
from cmdb.registry import TypeRegistry
from .serializers import (
    NodeTypeSerializer, NodeSerializer, NodeDetailSerializer,
    NodeCreateUpdateSerializer, RelationshipCreateSerializer
)

# Import audit log utility if available
try:
    import sys
    import os
    from django.conf import settings
    feature_packs_path = os.path.join(settings.BASE_DIR, 'feature_packs')
    if feature_packs_path not in sys.path:
        sys.path.insert(0, feature_packs_path)
    from audit_log_pack.views import create_audit_entry
except ImportError:
    def create_audit_entry(*args, **kwargs):
        pass


class NodeTypeViewSet(viewsets.ViewSet):
    """
    ViewSet for listing node types/labels.
    
    list: Get all registered node types with their metadata
    """
    
    def list(self, request):
        """
        List all registered node types/labels.
        GET /api/types/
        """
        try:
            types_data = []
            for label in TypeRegistry.known_labels():
                metadata = TypeRegistry.get_metadata(label)
                types_data.append({
                    'label': label,
                    'display_name': metadata.get('display_name', label),
                    'category': metadata.get('category', 'Uncategorized'),
                    'description': metadata.get('description', ''),
                    'properties': metadata.get('properties', []),
                    'required': metadata.get('required', []),
                    'relationships': metadata.get('relationships', {}),
                })
            
            serializer = NodeTypeSerializer(types_data, many=True)
            return Response({
                'success': True,
                'types': serializer.data,
                'count': len(types_data)
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NodeViewSet(viewsets.ViewSet):
    """
    ViewSet for CRUD operations on nodes.
    
    list: Get all nodes of a specific type
    retrieve: Get a specific node by ID
    create: Create a new node
    update: Update an existing node
    partial_update: Partially update an existing node
    destroy: Delete a node
    connect: Create a relationship between nodes
    disconnect: Remove a relationship between nodes
    """
    
    def list(self, request, label=None):
        """
        List all nodes of a specific type/label.
        GET /api/nodes/<label>/
        
        Query Parameters:
            - limit: Max number of results (default: 100)
            - offset: Number of results to skip for pagination (default: 0)
        """
        try:
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            node_class = DynamicNode.get_or_create_label(label)
            nodes = node_class.nodes.all()[offset:offset + limit]
            
            serializer = NodeSerializer(nodes, many=True)
            return Response({
                'success': True,
                'label': label,
                'nodes': serializer.data,
                'count': len(serializer.data),
                'limit': limit,
                'offset': offset
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, label=None, pk=None):
        """
        Get a specific node by its element ID.
        GET /api/nodes/<label>/<element_id>/
        """
        try:
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            node_class = DynamicNode.get_or_create_label(label)
            node = node_class.get_by_element_id(pk)
            
            if not node:
                return Response({
                    'success': False,
                    'error': 'Node not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = NodeDetailSerializer(node)
            return Response({
                'success': True,
                'node': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, label=None):
        """
        Create a new node of the specified type.
        POST /api/nodes/<label>/
        
        Request Body:
            {
                "properties": {
                    "name": "Server-01",
                    "status": "active",
                    ...
                }
            }
        """
        try:
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = NodeCreateUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Invalid request data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            properties = serializer.validated_data['properties']
            
            # Validate required properties
            metadata = TypeRegistry.get_metadata(label)
            required_props = metadata.get('required', [])
            for req_prop in required_props:
                if req_prop not in properties:
                    return Response({
                        'success': False,
                        'error': f'Missing required property: {req_prop}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create node
            node_class = DynamicNode.get_or_create_label(label)
            node = node_class(custom_properties=properties).save()
            
            # Create audit log entry
            create_audit_entry(
                action='CREATE',
                node_label=label,
                node_id=node.element_id,
                user=request.user.username if request.user.is_authenticated else 'api_user',
                details=f"Created via API with properties: {list(properties.keys())}"
            )
            
            result_serializer = NodeSerializer(node)
            return Response({
                'success': True,
                'node': result_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, label=None, pk=None):
        """
        Update an existing node (full update).
        PUT /api/nodes/<label>/<element_id>/
        """
        return self._update_node(request, label, pk, partial=False)
    
    def partial_update(self, request, label=None, pk=None):
        """
        Partially update an existing node.
        PATCH /api/nodes/<label>/<element_id>/
        """
        return self._update_node(request, label, pk, partial=True)
    
    def _update_node(self, request, label, pk, partial=True):
        """Helper method for updating nodes."""
        try:
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = NodeCreateUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Invalid request data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            new_properties = serializer.validated_data['properties']
            
            # Get existing node
            node_class = DynamicNode.get_or_create_label(label)
            node = node_class.get_by_element_id(pk)
            
            if not node:
                return Response({
                    'success': False,
                    'error': 'Node not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Update properties
            current_props = node.custom_properties or {}
            current_props.update(new_properties)
            node.custom_properties = current_props
            node.save()
            
            # Create audit log entry
            create_audit_entry(
                action='UPDATE',
                node_label=label,
                node_id=node.element_id,
                user=request.user.username if request.user.is_authenticated else 'api_user',
                details=f"Updated via API: {list(new_properties.keys())}"
            )
            
            result_serializer = NodeSerializer(node)
            return Response({
                'success': True,
                'node': result_serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, label=None, pk=None):
        """
        Delete a node.
        DELETE /api/nodes/<label>/<element_id>/
        """
        try:
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get node
            node_class = DynamicNode.get_or_create_label(label)
            node = node_class.get_by_element_id(pk)
            
            if not node:
                return Response({
                    'success': False,
                    'error': 'Node not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get node name for audit log before deletion
            node_name = (node.custom_properties or {}).get('name', pk[:8])
            
            # Delete node
            node.delete()
            
            # Create audit log entry
            create_audit_entry(
                action='DELETE',
                node_label=label,
                node_id=pk,
                user=request.user.username if request.user.is_authenticated else 'api_user',
                details=f"Deleted via API: {node_name}"
            )
            
            return Response({
                'success': True,
                'message': 'Node deleted successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def relationships(self, request, label=None, pk=None):
        """
        Create a relationship between two nodes.
        POST /api/nodes/<label>/<element_id>/relationships/
        
        Request Body:
            {
                "relationship_type": "LOCATED_IN",
                "target_label": "Room",
                "target_id": "4:xyz789..."
            }
        """
        try:
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = RelationshipCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Invalid request data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            rel_type = serializer.validated_data['relationship_type']
            target_label = serializer.validated_data['target_label']
            target_id = serializer.validated_data['target_id']
            
            # Validate target label exists
            if target_label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown target node type: {target_label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Connect nodes
            success = DynamicNode.connect_nodes(
                pk, label,
                rel_type,
                target_id, target_label
            )
            
            if not success:
                return Response({
                    'success': False,
                    'error': 'Failed to create relationship. Check if both nodes exist.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create audit log entry
            create_audit_entry(
                action='CONNECT',
                node_label=label,
                node_id=pk,
                user=request.user.username if request.user.is_authenticated else 'api_user',
                details=f"Created relationship {rel_type} to {target_label}:{target_id[:8]}..."
            )
            
            return Response({
                'success': True,
                'message': 'Relationship created successfully'
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='relationships/(?P<relationship_type>[^/.]+)/(?P<target_id>[^/.]+)')
    def disconnect(self, request, label=None, pk=None, relationship_type=None, target_id=None):
        """
        Remove a relationship between two nodes.
        DELETE /api/nodes/<label>/<element_id>/relationships/<relationship_type>/<target_id>/
        """
        try:
            # Validate label exists
            if label not in TypeRegistry.known_labels():
                return Response({
                    'success': False,
                    'error': f'Unknown node type: {label}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get source node to verify it exists
            node_class = DynamicNode.get_or_create_label(label)
            source_node = node_class.get_by_element_id(pk)
            
            if not source_node:
                return Response({
                    'success': False,
                    'error': 'Source node not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Find the target node's label
            query = """
                MATCH (n) WHERE elementId(n) = $tid
                RETURN labels(n)[0] AS label
            """
            result, _ = db.cypher_query(query, {'tid': target_id})
            
            if not result:
                return Response({
                    'success': False,
                    'error': 'Target node not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            target_label = result[0][0]
            
            # Disconnect nodes
            deleted = DynamicNode.disconnect_nodes(
                pk, label,
                relationship_type,
                target_id, target_label
            )
            
            if deleted == 0:
                return Response({
                    'success': False,
                    'error': 'Relationship not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Create audit log entry
            create_audit_entry(
                action='DISCONNECT',
                node_label=label,
                node_id=pk,
                user=request.user.username if request.user.is_authenticated else 'api_user',
                details=f"Removed relationship {relationship_type} to {target_label}:{target_id[:8]}..."
            )
            
            return Response({
                'success': True,
                'message': 'Relationship removed successfully'
            })
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
