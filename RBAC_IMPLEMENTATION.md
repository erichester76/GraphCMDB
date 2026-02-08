# RBAC Implementation Summary

## Overview
Implemented comprehensive Role-Based Access Control (RBAC) with dynamic permissions for all node types in GraphCMDB.

## What Was Implemented

### 1. Dynamic Permission Creation (`cmdb/permissions.py`)

Created utilities to automatically generate Django permissions for each node type:

**Functions:**
- `create_permissions_for_node_type(label)` - Creates 4 permissions per type:
  - `view_{label}` - Can view {label}
  - `add_{label}` - Can add {label}
  - `change_{label}` - Can change {label}
  - `delete_{label}` - Can delete {label}

- `sync_all_node_type_permissions()` - Syncs permissions for all registered types
- `delete_permissions_for_node_type(label)` - Removes permissions when type is unregistered

**Integration:**
- Permissions are automatically created during feature pack loading (`core/apps.py`)
- Uses Django's ContentType system with `cmdb.dynamicnode` as the content type
- Permissions follow Django naming convention: `cmdb.action_nodetype`

### 2. Enhanced Permission Checking (`users/views.py`)

Updated `has_node_permission(user, action, label)` function:
- **Superusers**: Have all permissions (unchanged)
- **Staff users**: Now require explicit permissions (changed from automatic all-access)
- **Regular users**: Must have explicit permission via user permissions or group membership
- **Permission format**: `cmdb.view_device`, `cmdb.add_network`, etc.

Added `node_permission_required(action, label_param='label')` decorator:
- Automatically checks if user has permission for the action on the node type
- Redirects to login if not authenticated
- Redirects to dashboard with error message if not authorized

### 3. Protected Views (`cmdb/views.py`)

Added decorators to all node-related views:

| View | Decorators | Required Permission |
|------|-----------|-------------------|
| `nodes_list` | `@login_required` `@node_permission_required('view')` | view_{label} |
| `node_detail` | `@login_required` `@node_permission_required('view')` | view_{label} |
| `node_create` | `@login_required` `@node_permission_required('add')` | add_{label} |
| `node_edit` | `@login_required` `@node_permission_required('change')` | change_{label} |
| `node_delete` | `@login_required` `@node_permission_required('delete')` | delete_{label} |
| `node_connect` | `@login_required` `@node_permission_required('change')` | change_{label} |
| `node_disconnect` | `@login_required` `@node_permission_required('change')` | change_{label} |
| `node_import` | `@login_required` `@node_permission_required('add')` | add_{label} |

### 4. Protected Feature Pack Views (`cmdb/feature_pack_views.py`)

All feature pack management views now require staff privileges:
- `feature_pack_list` - `@login_required` `@user_passes_test(is_staff_user)`
- `feature_pack_detail` - `@login_required` `@user_passes_test(is_staff_user)`
- `feature_pack_enable` - `@login_required` `@user_passes_test(is_staff_user)`
- `feature_pack_disable` - `@login_required` `@user_passes_test(is_staff_user)`
- `feature_pack_status_api` - `@login_required` `@user_passes_test(is_staff_user)`

### 5. Permission-Aware Templates

#### Context Processors (`cmdb/context_processors.py`)

**Enhanced `categories_context()`:**
- Automatically filters sidebar categories based on user's view permissions
- Only shows node types the user has `view` permission for
- Empty categories are automatically hidden

**Added `user_permissions_context()`:**
- Provides `can_user(action, label)` helper function to all templates
- Allows templates to check permissions: `{% if can_user 'add' 'Device' %}`

#### Sidebar (`cmdb/templates/base.html`)
- Node types user can't view are hidden (automatic via context processor)
- Create and Import buttons hidden if user lacks `add` permission:
  ```django
  {% if can_user 'add' label %}
  <button>Create {{ label }}</button>
  <button>Import {{ label }}</button>
  {% endif %}
  ```

#### Node List Table (`cmdb/templates/cmdb/partials/nodes_table.html`)
- "Detail" link hidden if user lacks `view` permission
- "Delete" button hidden if user lacks `delete` permission

#### Node Detail Page (`cmdb/templates/cmdb/partials/node_detail_content.html`)
- "Edit" button hidden if user lacks `change` permission
- "Delete" button hidden if user lacks `delete` permission

### 6. Comprehensive Tests (`cmdb/tests/test_permissions.py`)

Created test suite covering:
- **DynamicPermissionCreationTest**: Tests permission creation, idempotency, deletion, and sync
- **PermissionCheckingTest**: Tests permission logic for superusers, staff, regular users, and groups
- **PermissionDecoratorTest**: Tests that view decorators correctly enforce permissions
- **ContextProcessorTest**: Tests that context processors filter based on permissions

**Test Coverage:**
- Permission creation for node types
- Permission checking for different user types
- View decorator enforcement
- Context processor filtering
- Group-based permissions
- User-specific permissions

## How It Works

### Permission Lifecycle

1. **Feature Pack Load** (`core/apps.py`)
   - Feature packs are loaded and types registered
   - `sync_all_node_type_permissions()` is called
   - Permissions created for all registered node types

2. **User Access** 
   - User navigates to a page
   - `@node_permission_required` decorator checks permission
   - If unauthorized, redirected with error message

3. **Template Rendering**
   - `categories_context()` filters sidebar by view permissions
   - `can_user()` helper checks permissions for UI elements
   - Unauthorized buttons/links are hidden

### Permission Assignment

**Via Django Admin:**
1. Navigate to `/admin/auth/user/`
2. Edit user
3. Assign permissions directly or add to groups

**Via Groups (Recommended):**
1. Create group (e.g., "Network Admins")
2. Assign permissions to group (e.g., `cmdb.view_network`, `cmdb.change_network`)
3. Add users to group
4. All group members inherit permissions

### Example Scenarios

**Scenario 1: View-Only User**
```python
# Create viewer group
viewers = Group.objects.create(name='Viewers')

# Add view permissions for specific types
for node_type in ['Device', 'Network', 'Site']:
    perm = Permission.objects.get(codename=f'view_{node_type.lower()}')
    viewers.permissions.add(perm)

# Add user to group
user.groups.add(viewers)
```

**Scenario 2: Network Administrator**
```python
# Create network admin group
net_admins = Group.objects.create(name='Network Admins')

# Add all permissions for network-related types
for node_type in ['Network', 'IP_Address', 'Interface', 'VLAN']:
    for action in ['view', 'add', 'change', 'delete']:
        perm = Permission.objects.get(codename=f'{action}_{node_type.lower()}')
        net_admins.permissions.add(perm)

# Add user to group
user.groups.add(net_admins)
```

## Benefits

1. **Fine-Grained Control**: Permissions down to individual node types and actions
2. **Group-Based Management**: Easy to manage permissions via groups
3. **Automatic UI Updates**: UI automatically hides unauthorized actions
4. **Security by Default**: All views require explicit permissions
5. **Django Standards**: Uses Django's built-in permission system
6. **Extensible**: Easy to add new node types - permissions created automatically
7. **Auditable**: All permissions tracked in Django's auth system

## Migration Path for Existing Installations

For existing installations:

1. **Run migrations** to ensure permission tables are ready
2. **Restart server** to trigger permission sync
3. **Assign permissions** to existing users/groups
4. **Test access** with regular user accounts

**Quick Setup for Testing:**
```bash
# Create a test user
python manage.py shell
>>> from django.contrib.auth.models import User, Group, Permission
>>> user = User.objects.create_user('testuser', password='testpass')

# Give view permission for all types
>>> for perm in Permission.objects.filter(codename__startswith='view_', content_type__app_label='cmdb'):
...     user.user_permissions.add(perm)

# Test login
# Navigate to /users/login/ and login with testuser/testpass
```

## Future Enhancements

Potential improvements:
- **Object-level permissions**: Permissions on specific node instances
- **Permission templates**: Pre-configured permission sets for common roles
- **Permission API**: REST API for managing permissions programmatically
- **Audit logging**: Log all permission checks and failures
- **Permission inheritance**: Permissions that cascade through relationships

## Troubleshooting

**Issue: User can't see any node types in sidebar**
- Check user has at least one `view_*` permission
- Verify permissions were created: `Permission.objects.filter(content_type__app_label='cmdb')`

**Issue: Permissions not created for new types**
- Restart server to trigger permission sync
- Manually run: `from cmdb.permissions import sync_all_node_type_permissions; sync_all_node_type_permissions()`

**Issue: Staff user can't access features**
- Staff users now require explicit permissions
- Add permissions via Django admin or assign to appropriate groups

## Security Considerations

- ✅ All views protected with decorators
- ✅ Templates check permissions before showing actions
- ✅ Staff no longer have automatic all-access (principle of least privilege)
- ✅ Superusers retain all permissions (for emergency access)
- ✅ Permissions follow Django standards (auditable, manageable)
- ✅ Context processors prevent information leakage via sidebar

## Files Modified

- `cmdb/permissions.py` - NEW - Permission creation utilities
- `cmdb/views.py` - Added decorators to all node views
- `cmdb/feature_pack_views.py` - Added staff-only decorators
- `cmdb/context_processors.py` - Enhanced with permission filtering
- `cmdb/templates/base.html` - Added permission checks for create/import buttons
- `cmdb/templates/cmdb/partials/nodes_table.html` - Added permission checks for actions
- `cmdb/templates/cmdb/partials/node_detail_content.html` - Added permission checks for edit/delete
- `cmdb/tests/test_permissions.py` - NEW - Comprehensive test suite
- `core/apps.py` - Added permission sync on startup
- `core/settings.py` - Added new context processor
- `users/views.py` - Enhanced permission checking logic

## Conclusion

The RBAC implementation provides enterprise-grade access control for GraphCMDB. All node types automatically get permissions, all views are protected, and the UI adapts based on user permissions. This ensures security while maintaining usability.
