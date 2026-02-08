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
        'audit_entries': [],
        'error': None,
    }

    try:
        # Fetch audit log entries related to this node
        query = """
            MATCH (log:AuditLogEntry)
            WHERE apoc.convert.fromJsonMap(log.custom_properties).node_id = $eid
            WITH log, apoc.convert.fromJsonMap(log.custom_properties) AS props
            RETURN 
                elementId(log) AS id,
                props.timestamp AS timestamp,
                props.action AS action,
                props.node_label AS node_label,
                props.node_name AS node_name,
                props.user AS user,
                props.changes AS changes,
                props.relationship_type AS relationship_type,
                props.target_label AS target_label,
                props.target_id AS target_id
            ORDER BY props.timestamp DESC
            LIMIT 100
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        
        for row in result:
            context['audit_entries'].append({
                'id': row[0],
                'timestamp': row[1],
                'action': row[2],
                'node_label': row[3],
                'node_name': row[4] or 'Unknown',
                'user': row[5] or 'System',
                'changes': row[6],
                'relationship_type': row[7],
                'target_label': row[8],
                'target_id': row[9]
            })

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
