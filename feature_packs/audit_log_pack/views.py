# feature_packs/audit_log_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode
from datetime import datetime, timezone


def audit_log_tab(request, label, element_id):
    """
    Custom view for Audit Log tab on node detail pages.
    Shows audit log entries filtered to the specific node.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'custom_data': {
            'audit_entries': []
        },
        'error': None,
    }

    try:
        # Fetch all audit log entries using neomodel (same as global view)
        audit_node_class = DynamicNode.get_or_create_label('AuditLogEntry')
        all_audit_nodes = audit_node_class.nodes.all()
        
        # Filter to only entries for this specific node and extract properties
        audit_entries = []
        for node in all_audit_nodes:
            props = node.custom_properties or {}
            # Filter by node_id matching the element_id
            if props.get('node_id') == element_id:
                audit_entries.append({
                    'id': node.element_id,
                    'timestamp': props.get('timestamp', ''),
                    'action': props.get('action', ''),
                    'node_label': props.get('node_label', ''),
                    'node_name': props.get('node_name', 'Unknown'),
                    'user': props.get('user', 'System'),
                    'changes': props.get('changes', ''),
                    'relationship_type': props.get('relationship_type', ''),
                    'target_label': props.get('target_label', ''),
                    'target_id': props.get('target_id', '')
                })
        
        # Sort by timestamp descending (most recent first) and limit to 100
        audit_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        context['custom_data']['audit_entries'] = audit_entries[:100]

    except Exception as e:
        context['error'] = str(e)

    return context


def create_audit_entry(action, node_label, node_id, node_name=None, user=None, changes=None, 
                       relationship_type=None, target_label=None, target_id=None):
    """
    Utility function to create an audit log entry.
    
    Args:
        action: Type of action (create, update, delete, connect, disconnect)
        node_label: Label of the node being modified
        node_id: Element ID of the node being modified
        node_name: Name of the node (optional)
        user: User performing the action (optional)
        changes: Description of changes (optional)
        relationship_type: For relationship actions (optional)
        target_label: For relationship actions (optional)
        target_id: For relationship actions (optional)
    """
    try:
        audit_node_class = DynamicNode.get_or_create_label('AuditLogEntry')
        
        properties = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'node_label': node_label,
            'node_id': node_id,
            'node_name': node_name or '',
            'user': user or 'System',
            'changes': changes or '',
            'relationship_type': relationship_type or '',
            'target_label': target_label or '',
            'target_id': target_id or ''
        }
        
        audit_node = audit_node_class(custom_properties=properties).save()
        return audit_node
    except Exception as e:
        # Log the error but don't fail the main operation
        print(f"Error creating audit log entry: {e}")
        return None
