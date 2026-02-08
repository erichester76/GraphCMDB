"""
Utilities for creating and managing dynamic permissions for node types.
"""
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.apps import apps


def create_permissions_for_node_type(label):
    """
    Create Django permissions for a node type.
    
    Creates four permissions:
    - view_{label_lower}: Can view {label}
    - add_{label_lower}: Can add {label}
    - change_{label_lower}: Can change {label}
    - delete_{label_lower}: Can delete {label}
    
    Args:
        label: The node type label (e.g., 'Device', 'Network')
    
    Returns:
        list: List of Permission objects created or retrieved
    """
    # Get or create a ContentType for CMDB
    # We'll use a dummy model ContentType for all dynamic node types
    try:
        cmdb_app = apps.get_app_config('cmdb')
        # Use the first model in cmdb app as the content type
        # This is a workaround since we don't have actual models for dynamic types
        content_type, _ = ContentType.objects.get_or_create(
            app_label='cmdb',
            model='dynamicnode',
        )
    except Exception as e:
        print(f"[WARNING] Could not get ContentType for permissions: {e}")
        return []
    
    label_lower = label.lower()
    permissions = []
    
    permission_specs = [
        ('view', f'Can view {label}'),
        ('add', f'Can add {label}'),
        ('change', f'Can change {label}'),
        ('delete', f'Can delete {label}'),
    ]
    
    for action, name in permission_specs:
        codename = f'{action}_{label_lower}'
        perm, created = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )
        permissions.append(perm)
        
        if created:
            print(f"[DEBUG] Created permission: {codename} ({name})")
        else:
            # Update name if it changed
            if perm.name != name:
                perm.name = name
                perm.save()
                print(f"[DEBUG] Updated permission: {codename} ({name})")
    
    return permissions


def sync_all_node_type_permissions():
    """
    Sync permissions for all registered node types.
    Should be called after feature packs are loaded.
    
    Returns:
        dict: Statistics about permissions created
    """
    from cmdb.registry import TypeRegistry
    
    stats = {
        'total_types': 0,
        'total_permissions': 0,
        'types_processed': [],
    }
    
    for label in TypeRegistry.known_labels():
        perms = create_permissions_for_node_type(label)
        stats['total_types'] += 1
        stats['total_permissions'] += len(perms)
        stats['types_processed'].append(label)
    
    print(f"[DEBUG] Permission sync complete: {stats['total_types']} types, {stats['total_permissions']} permissions")
    return stats


def delete_permissions_for_node_type(label):
    """
    Delete permissions for a node type when it's unregistered.
    
    Args:
        label: The node type label
        
    Returns:
        int: Number of permissions deleted
    """
    try:
        content_type = ContentType.objects.get(
            app_label='cmdb',
            model='dynamicnode',
        )
    except ContentType.DoesNotExist:
        return 0
    
    label_lower = label.lower()
    count = 0
    
    for action in ['view', 'add', 'change', 'delete']:
        codename = f'{action}_{label_lower}'
        deleted, _ = Permission.objects.filter(
            codename=codename,
            content_type=content_type
        ).delete()
        count += deleted
    
    if count > 0:
        print(f"[DEBUG] Deleted {count} permissions for {label}")
    
    return count
