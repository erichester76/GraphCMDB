# cmdb/context_processors.py
from .registry import TypeRegistry


def categories_context(request):
    """
    Add categories and their types to template context.
    Now filters based on user permissions.
    """
    from users.views import has_node_permission
    
    all_categories = TypeRegistry.get_categories()
    
    # Filter categories based on user permissions
    filtered_categories = {}
    if request.user.is_authenticated:
        for category, labels in all_categories.items():
            # Filter labels user can view
            visible_labels = [
                label for label in labels 
                if has_node_permission(request.user, 'view', label)
            ]
            if visible_labels:
                filtered_categories[category] = visible_labels
    else:
        # Not authenticated - show nothing
        filtered_categories = {}
    
    # Get metadata for icons and display
    categories_metadata = {}
    for label in TypeRegistry.known_labels():
        meta = TypeRegistry.get_metadata(label)
        categories_metadata[label] = meta
    
    return {
        'categories': filtered_categories,
        'categories_metadata': categories_metadata,
    }


def user_permissions_context(request):
    """
    Add user permission checking function to template context.
    """
    from users.views import has_node_permission
    
    def can_user(action, label=None):
        """Helper function for templates to check permissions."""
        if not request.user.is_authenticated:
            return False
        return has_node_permission(request.user, action, label)
    
    return {
        'can_user': can_user,
    }
