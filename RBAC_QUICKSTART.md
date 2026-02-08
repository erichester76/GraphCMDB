# RBAC Implementation - Quick Start Guide

## What Was Added

Dynamic permissions and role-based access control for all node types in GraphCMDB.

## For Administrators

### First Time Setup

1. **Permissions are created automatically** when the server starts
   - Each node type gets 4 permissions: view, add, change, delete
   - Format: `cmdb.view_device`, `cmdb.add_network`, etc.

2. **Create roles using Groups**
   ```bash
   # Via Django Admin (recommended)
   # 1. Go to /admin/auth/group/
   # 2. Click "Add group"
   # 3. Name it (e.g., "Network Admins")
   # 4. Select permissions
   # 5. Save
   ```

3. **Assign users to groups**
   ```bash
   # Via Django Admin
   # 1. Go to /admin/auth/user/
   # 2. Edit user
   # 3. Select groups in "Groups" section
   # 4. Save
   ```

### Common Role Examples

**View-Only Users**
- Permissions: All `view_*` permissions
- Can: Browse and view all node types
- Cannot: Create, edit, or delete anything

**Network Administrators**
- Permissions: All permissions for Network, IP_Address, Interface, VLAN, etc.
- Can: Full control over network-related nodes
- Cannot: Modify other node types

**IT Operators**
- Permissions: Most `view_*`, selected `change_*` and `add_*`
- Can: View everything, modify specific types
- Cannot: Delete critical nodes

**Full Administrators**
- Make user `is_superuser = True`
- Has: All permissions automatically
- Use: For system administrators only

## For Users

### What Changed

**Sidebar**
- You only see node types you have permission to view
- Create/Import buttons only show if you can add that type

**Node Lists**
- Detail link only shows if you can view
- Delete button only shows if you can delete

**Node Detail Pages**
- Edit button only shows if you can change
- Delete button only shows if you can delete

**Feature Packs**
- Only staff users can manage feature packs

### If You Can't See Something

Check with your administrator to verify you have the correct permissions:
1. Navigate to your profile: `/users/profile/`
2. Check your groups
3. Ask admin to verify group permissions

## For Developers

### Checking Permissions in Code

```python
from users.views import has_node_permission

# Check if user has permission
if has_node_permission(request.user, 'change', 'Device'):
    # User can modify Device nodes
    pass
```

### Using Decorators

```python
from users.views import node_permission_required

@login_required
@node_permission_required('delete')
def my_view(request, label, element_id):
    # Only users with delete permission can access
    pass
```

### Checking in Templates

```django
{% if can_user 'add' 'Device' %}
<button>Create Device</button>
{% endif %}

{% if can_user 'delete' label %}
<button>Delete</button>
{% endif %}
```

## Permission Reference

| Action | Permission | Allows |
|--------|-----------|--------|
| `view` | `view_{nodetype}` | View nodes in lists and detail pages |
| `add` | `add_{nodetype}` | Create new nodes, import nodes |
| `change` | `change_{nodetype}` | Edit nodes, connect/disconnect relationships |
| `delete` | `delete_{nodetype}` | Delete nodes |

## Troubleshooting

**Q: User can't see any node types**
- A: Add at least one `view_*` permission to the user or their group

**Q: Staff user can't access features**
- A: Staff users need explicit permissions now (changed from automatic all-access)

**Q: New node type doesn't have permissions**
- A: Restart the server to trigger permission sync

**Q: How do I give full access?**
- A: Make user superuser OR add all permissions to a group and assign user to it

## Migration from Previous Version

If upgrading from a version without RBAC:

1. **Restart server** - Permissions will be created automatically
2. **Superusers unchanged** - They still have full access
3. **Staff users** - Now need explicit permissions, assign via groups
4. **Regular users** - Need permissions assigned to access anything

**Quick fix for staff users:**
```python
# Via Django shell (python manage.py shell)
from django.contrib.auth.models import User, Group, Permission

# Create "All Access" group for staff
all_access = Group.objects.create(name='All Access')

# Add all CMDB permissions
for perm in Permission.objects.filter(content_type__app_label='cmdb'):
    all_access.permissions.add(perm)

# Add all staff users to this group
for user in User.objects.filter(is_staff=True, is_superuser=False):
    user.groups.add(all_access)
```

## Security Best Practices

1. ✅ **Use Groups** - Don't assign permissions directly to users
2. ✅ **Least Privilege** - Give minimum permissions needed
3. ✅ **Regular Audits** - Review user permissions periodically
4. ✅ **Superuser Sparingly** - Only for true administrators
5. ✅ **Test Access** - Verify users can't access unauthorized resources

## Getting Help

- **Full Documentation**: See `RBAC_IMPLEMENTATION.md`
- **User Guide**: See `docs/USERS_AND_RBAC.md`
- **Test Examples**: See `cmdb/tests/test_permissions.py`
