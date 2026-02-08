# Template Syntax Error Fix - Summary

## Problem
Template error reported at line 151 in `cmdb/templates/base.html`:
```
Unused 'add' at end of if expression
```

The problematic code was:
```django
{% if can_user 'add' label %}
```

## Root Cause
Django's template language doesn't support calling functions with multiple positional arguments directly in `{% if %}` tags. The syntax `can_user 'add' label` was being interpreted incorrectly, with Django trying to treat `'add'` as a filter and `label` as an argument, which resulted in the "unused 'add'" error.

## Solution
Created a custom template tag `user_can` that properly handles permission checking in templates.

### Changes Made

#### 1. New Template Tag (`cmdb/templatetags/cmdb_extras.py`)
```python
@register.simple_tag(takes_context=True)
def user_can(context, action, label=None):
    """
    Template tag to check if user has permission for an action on a node type.
    
    Usage:
        {% user_can 'view' 'Device' as can_view %}
        {% if can_view %}...{% endif %}
    """
    from users.views import has_node_permission
    
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    
    return has_node_permission(request.user, action, label)
```

#### 2. Updated Templates

**Before:**
```django
{% if can_user 'add' label %}
    <button>Create</button>
{% endif %}
```

**After:**
```django
{% user_can 'add' label as can_add_node %}
{% if can_add_node %}
    <button>Create</button>
{% endif %}
```

**Files Updated:**
- `cmdb/templates/base.html` (line 151)
- `cmdb/templates/cmdb/partials/nodes_table.html`
- `cmdb/templates/cmdb/partials/node_detail_content.html`

#### 3. Added Tests (`cmdb/tests/test_templatetags.py`)
Created comprehensive tests for the new template tag covering:
- User with permission
- User without permission
- Variable labels
- Anonymous users
- Different actions

## How the Fix Works

The `@register.simple_tag(takes_context=True)` decorator allows us to:
1. Access the request context to get the current user
2. Accept multiple arguments properly
3. Return a value that can be stored in a variable

The pattern `{% user_can 'action' label as var_name %}` stores the result in `var_name`, which can then be used in conditional statements.

## Benefits
- ✅ Fixes the template syntax error
- ✅ Maintains same permission checking functionality
- ✅ Cleaner, more explicit template code
- ✅ Fully tested
- ✅ Works with both string literals and variables

## Usage Examples

```django
{# Check permission and store result #}
{% user_can 'view' 'Device' as can_view %}
{% if can_view %}
    <a href="...">View Device</a>
{% endif %}

{# With variable label #}
{% user_can 'add' label as can_add %}
{% if can_add %}
    <button>Create {{ label }}</button>
{% endif %}

{# Multiple checks #}
{% user_can 'change' node_type as can_change %}
{% user_can 'delete' node_type as can_delete %}
{% if can_change %}
    <button>Edit</button>
{% endif %}
{% if can_delete %}
    <button>Delete</button>
{% endif %}
```

## Testing
Run the template tag tests with:
```bash
python manage.py test cmdb.tests.test_templatetags
```

All tests verify:
- Correct permission checking
- Proper handling of authenticated/anonymous users
- Variable and literal argument support
- Multiple action types (view, add, change, delete)
