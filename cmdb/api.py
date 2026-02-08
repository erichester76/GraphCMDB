# cmdb/api.py
"""
REST API endpoints for CRUD operations on all node types.
Provides JSON-based API for external integrations and automation.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import DynamicNode
from .registry import TypeRegistry
from neomodel import db
import json


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


@require_http_methods(["GET"])
def api_list_node_types(request):
    """
    List all registered node types/labels.
    GET /api/types/
    
    Returns:
        {
            "success": true,
            "types": [
                {
                    "label": "Device",
                    "display_name": "Device",
                    "category": "Data Center",
                    "properties": [...],
                    "relationships": {...}
                },
                ...
            ]
        }
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
        
        return JsonResponse({
            'success': True,
            'types': types_data,
            'count': len(types_data)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_list_nodes(request, label):
    """
    List all nodes of a specific type/label.
    GET /api/nodes/<label>/
    
    Query Parameters:
        - limit: Max number of results (default: 100)
        - skip: Number of results to skip for pagination (default: 0)
    
    Returns:
        {
            "success": true,
            "label": "Device",
            "nodes": [
                {
                    "id": "4:abc123...",
                    "properties": {...}
                },
                ...
            ],
            "count": 42
        }
    """
    try:
        limit = int(request.GET.get('limit', 100))
        skip = int(request.GET.get('skip', 0))
        
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        node_class = DynamicNode.get_or_create_label(label)
        nodes = node_class.nodes.all()[skip:skip + limit]
        
        nodes_data = []
        for node in nodes:
            nodes_data.append({
                'id': node.element_id,
                'properties': node.custom_properties or {}
            })
        
        return JsonResponse({
            'success': True,
            'label': label,
            'nodes': nodes_data,
            'count': len(nodes_data),
            'limit': limit,
            'skip': skip
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_get_node(request, label, element_id):
    """
    Get a specific node by its element ID.
    GET /api/nodes/<label>/<element_id>/
    
    Returns:
        {
            "success": true,
            "node": {
                "id": "4:abc123...",
                "label": "Device",
                "properties": {...},
                "relationships": {
                    "outgoing": {...},
                    "incoming": {...}
                }
            }
        }
    """
    try:
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        node_class = DynamicNode.get_or_create_label(label)
        node = node_class.get_by_element_id(element_id)
        
        if not node:
            return JsonResponse({
                'success': False,
                'error': 'Node not found'
            }, status=404)
        
        # Get relationships
        out_rels = node.get_outgoing_relationships()
        in_rels = node.get_incoming_relationships()
        
        return JsonResponse({
            'success': True,
            'node': {
                'id': node.element_id,
                'label': label,
                'properties': node.custom_properties or {},
                'relationships': {
                    'outgoing': out_rels,
                    'incoming': in_rels
                }
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_create_node(request, label):
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
    
    Returns:
        {
            "success": true,
            "node": {
                "id": "4:abc123...",
                "label": "Device",
                "properties": {...}
            }
        }
    """
    try:
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        # Parse request body
        try:
            data = json.loads(request.body)
            properties = data.get('properties', {})
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        # Validate required properties
        metadata = TypeRegistry.get_metadata(label)
        required_props = metadata.get('required', [])
        for req_prop in required_props:
            if req_prop not in properties:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required property: {req_prop}'
                }, status=400)
        
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
        
        return JsonResponse({
            'success': True,
            'node': {
                'id': node.element_id,
                'label': label,
                'properties': node.custom_properties or {}
            }
        }, status=201)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def api_update_node(request, label, element_id):
    """
    Update an existing node.
    PUT/PATCH /api/nodes/<label>/<element_id>/
    
    Request Body:
        {
            "properties": {
                "status": "maintenance",
                ...
            }
        }
    
    Returns:
        {
            "success": true,
            "node": {
                "id": "4:abc123...",
                "label": "Device",
                "properties": {...}
            }
        }
    """
    try:
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        # Parse request body
        try:
            data = json.loads(request.body)
            new_properties = data.get('properties', {})
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        # Get existing node
        node_class = DynamicNode.get_or_create_label(label)
        node = node_class.get_by_element_id(element_id)
        
        if not node:
            return JsonResponse({
                'success': False,
                'error': 'Node not found'
            }, status=404)
        
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
        
        return JsonResponse({
            'success': True,
            'node': {
                'id': node.element_id,
                'label': label,
                'properties': node.custom_properties or {}
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_node(request, label, element_id):
    """
    Delete a node.
    DELETE /api/nodes/<label>/<element_id>/
    
    Returns:
        {
            "success": true,
            "message": "Node deleted successfully"
        }
    """
    try:
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        # Get node
        node_class = DynamicNode.get_or_create_label(label)
        node = node_class.get_by_element_id(element_id)
        
        if not node:
            return JsonResponse({
                'success': False,
                'error': 'Node not found'
            }, status=404)
        
        # Get node name for audit log before deletion
        node_name = (node.custom_properties or {}).get('name', element_id[:8])
        
        # Delete node
        node.delete()
        
        # Create audit log entry
        create_audit_entry(
            action='DELETE',
            node_label=label,
            node_id=element_id,
            user=request.user.username if request.user.is_authenticated else 'api_user',
            details=f"Deleted via API: {node_name}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Node deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_connect_nodes(request, label, element_id):
    """
    Create a relationship between two nodes.
    POST /api/nodes/<label>/<element_id>/relationships/
    
    Request Body:
        {
            "relationship_type": "LOCATED_IN",
            "target_label": "Room",
            "target_id": "4:xyz789..."
        }
    
    Returns:
        {
            "success": true,
            "message": "Relationship created successfully"
        }
    """
    try:
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        # Parse request body
        try:
            data = json.loads(request.body)
            rel_type = data.get('relationship_type')
            target_label = data.get('target_label')
            target_id = data.get('target_id')
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        if not all([rel_type, target_label, target_id]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: relationship_type, target_label, target_id'
            }, status=400)
        
        # Validate target label exists
        if target_label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown target node type: {target_label}'
            }, status=404)
        
        # Connect nodes
        success = DynamicNode.connect_nodes(
            element_id, label,
            rel_type,
            target_id, target_label
        )
        
        if not success:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create relationship. Check if both nodes exist.'
            }, status=400)
        
        # Create audit log entry
        create_audit_entry(
            action='CONNECT',
            node_label=label,
            node_id=element_id,
            user=request.user.username if request.user.is_authenticated else 'api_user',
            details=f"Created relationship {rel_type} to {target_label}:{target_id[:8]}..."
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Relationship created successfully'
        }, status=201)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_disconnect_nodes(request, label, element_id, relationship_type, target_id):
    """
    Remove a relationship between two nodes.
    DELETE /api/nodes/<label>/<element_id>/relationships/<relationship_type>/<target_id>/
    
    Returns:
        {
            "success": true,
            "message": "Relationship removed successfully"
        }
    """
    try:
        # Validate label exists
        if label not in TypeRegistry.known_labels():
            return JsonResponse({
                'success': False,
                'error': f'Unknown node type: {label}'
            }, status=404)
        
        # Get source node to verify it exists
        node_class = DynamicNode.get_or_create_label(label)
        source_node = node_class.get_by_element_id(element_id)
        
        if not source_node:
            return JsonResponse({
                'success': False,
                'error': 'Source node not found'
            }, status=404)
        
        # We need to find the target node's label
        # Query to find the target node and get its label
        query = """
            MATCH (n) WHERE elementId(n) = $tid
            RETURN labels(n)[0] AS label
        """
        result, _ = db.cypher_query(query, {'tid': target_id})
        
        if not result:
            return JsonResponse({
                'success': False,
                'error': 'Target node not found'
            }, status=404)
        
        target_label = result[0][0]
        
        # Disconnect nodes
        deleted = DynamicNode.disconnect_nodes(
            element_id, label,
            relationship_type,
            target_id, target_label
        )
        
        if deleted == 0:
            return JsonResponse({
                'success': False,
                'error': 'Relationship not found'
            }, status=404)
        
        # Create audit log entry
        create_audit_entry(
            action='DISCONNECT',
            node_label=label,
            node_id=element_id,
            user=request.user.username if request.user.is_authenticated else 'api_user',
            details=f"Removed relationship {relationship_type} to {target_label}:{target_id[:8]}..."
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Relationship removed successfully'
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
