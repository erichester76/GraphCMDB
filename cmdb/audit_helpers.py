import json
from cmdb.audit_hooks import emit_audit


def audit_update_node(label: str, element_id: str, old_props: dict, new_props: dict, user) -> None:
    node_name = new_props.get('name', '')
    changes_detail = {
        key: {
            'old': old_props.get(key),
            'new': new_props.get(key)
        }
        for key in set(old_props.keys()) | set(new_props.keys())
        if old_props.get(key) != new_props.get(key)
    }
    emit_audit(
        action='update',
        node_label=label,
        node_id=element_id,
        node_name=node_name,
        user=user.username if user and user.is_authenticated else 'System',
        changes=json.dumps(changes_detail, sort_keys=True, indent=2) if changes_detail else "Properties updated",
        old_props=old_props,
        new_props=new_props,
    )


def audit_create_node(label: str, element_id: str, props: dict, user) -> None:
    node_name = props.get('name', '')
    emit_audit(
        action='create',
        node_label=label,
        node_id=element_id,
        node_name=node_name,
        user=user.username if user and user.is_authenticated else 'System',
        changes=f"Created with properties: {', '.join(props.keys())}"
    )