from django import template

register = template.Library()

@register.filter
def property_display(prop):
    """
    Format a property definition for display.
    Handles both string properties and dict properties with choices.
    
    Examples:
        "name" -> "name"
        {"name": "status", "choices": ["active", "inactive"]} -> "status (choices: active, inactive)"
    """
    if isinstance(prop, str):
        return prop
    elif isinstance(prop, dict):
        name = prop.get('name', 'unknown')
        choices = prop.get('choices', [])
        if choices:
            choices_str = ', '.join(str(c) for c in choices)
            return f"{name} (choices: {choices_str})"
        return name
    return str(prop)

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.simple_tag(takes_context=True)
def user_can(context, action, label=None):
    """
    Template tag to check if user has permission for an action on a node type.
    
    Usage:
        {% user_can 'view' 'Device' as can_view %}
        {% if can_view %}...{% endif %}
        
        Or directly in if:
        {% user_can 'add' label as can_add %}
    """
    from users.views import has_node_permission
    
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    
    return has_node_permission(request.user, action, label)
