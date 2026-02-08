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
