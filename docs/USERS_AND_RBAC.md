# Users and RBAC Implementation

## Overview

This document describes the implementation of the Users subsystem with Role-Based Access Control (RBAC) in GraphCMDB. The implementation uses Django's built-in authentication system as the foundation, providing industry-standard security and user management capabilities.

## Architecture

### Django-Based Authentication

The Users subsystem is implemented as a core Django app (`users/`) rather than a feature pack, making it fundamental to the application. It leverages:

- **Django's built-in User model**: Provides username, password, email, first/last names, and basic flags (is_staff, is_superuser, is_active)
- **Django's Group model**: Used for implementing roles and organizing users
- **Django's Permission system**: Provides fine-grained access control

### Key Components

```
users/
├── __init__.py
├── admin.py          # Django admin configuration for Users and Groups
├── apps.py           # App configuration
├── models.py         # Uses Django's built-in User/Group models
├── views.py          # Authentication and user management views
├── urls.py           # URL routing for auth endpoints
├── tests.py          # Comprehensive test suite
└── templates/
    └── users/
        ├── login.html         # Login page
        ├── user_profile.html  # User profile page
        ├── user_list.html     # User management (staff only)
        └── group_list.html    # Role/group management (staff only)
```

## Features

### 1. Authentication

#### Login/Logout
- Secure login form with CSRF protection
- Password-based authentication
- Automatic redirection after login to requested page or dashboard
- Clean logout with confirmation message

**URLs:**
- Login: `/users/login/`
- Logout: `/users/logout/`

#### User Profile
- View current user information
- Display group memberships (roles)
- Show staff and superuser status
- Link to graph node if user exists in Neo4j

**URL:** `/users/profile/`

### 2. Role-Based Access Control (RBAC)

#### Permission Levels

**Superuser (is_superuser=True)**
- Full access to all system features
- Can manage all users and groups
- Access to Django admin panel
- All node operations (view, add, change, delete)

**Staff (is_staff=True)**
- Broad access to most features
- Can view and manage users and groups
- Access to Django admin panel
- Most node operations allowed

**Regular User**
- Limited access based on group membership
- No access to user/group management
- Permissions determined by assigned groups
- Can view their own profile

#### Group-Based Permissions

Groups (roles) provide flexible permission assignment:
- Users can belong to multiple groups
- Groups can have specific permissions assigned
- Permissions cascade to all group members
- Ideal for organizing users by department, project, or role

### 3. User Management (Staff Only)

#### User List (`/users/list/`)
- View all system users
- See user status (active/inactive, staff, admin)
- View group memberships
- Quick access to edit users in admin panel
- Create new users via admin link

#### Group List (`/users/groups/`)
- View all groups (roles)
- See member count and permission count
- View group members
- Quick access to edit groups in admin panel
- Create new groups via admin link

### 4. Permission Checking Utilities

The `users/views.py` module provides utilities for checking permissions:

```python
from users.views import has_node_permission, node_permission_required

# Check permissions programmatically
if has_node_permission(request.user, 'view', 'Device'):
    # User can view Device nodes
    pass

# Use decorator for view protection
@node_permission_required('change', label_param='label')
def edit_node(request, label, element_id):
    # Only users with 'change' permission for this node type can access
    pass
```

**Permission Actions:**
- `view`: Read access to nodes
- `add`: Create new nodes
- `change`: Edit existing nodes
- `delete`: Delete nodes

## Configuration

### Settings (core/settings.py)

```python
# Authentication settings
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/cmdb/'
LOGOUT_REDIRECT_URL = '/users/login/'

# Database for Django auth (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Installed apps
INSTALLED_APPS = [
    ...
    'users.apps.UsersConfig',   # Users & RBAC
    ...
]
```

### URLs (core/urls.py)

```python
urlpatterns = [
    path('users/', include('users.urls')),
    ...
]
```

## User Interface Integration

### Navigation Bar

The base template (`cmdb/templates/base.html`) includes:

**User Menu (Top Right)**
- Displays logged-in username
- Dropdown menu with:
  - Profile link
  - Admin link (staff only)
  - Logout link
- Login button when not authenticated

**Sidebar Links (Staff Only)**
- Users management link
- Groups (Roles) management link

### Visual Design

- Fully integrated with existing dark mode support
- Responsive design for mobile and desktop
- Consistent with CMDB UI patterns
- Uses Tailwind CSS and Alpine.js

## Security Features

### Built-in Django Security
- Password hashing (PBKDF2 with SHA256)
- CSRF protection on all forms
- Session-based authentication
- Password validation rules
- Protection against common attacks

### Access Control
- Login required for sensitive pages
- Staff-only restrictions on management pages
- Decorator-based permission checking
- Redirect to login for unauthorized access

### Best Practices
- Passwords never stored in plain text
- Secure session management
- Logout clears session data
- Messages for user feedback

## Usage Examples

### Creating Users

**Via Django Admin:**
1. Navigate to `/admin/`
2. Click "Users" → "Add user"
3. Enter username and password
4. Click "Save and continue editing"
5. Add additional information (email, name, groups, permissions)
6. Save

**Via Management Command:**
```bash
python manage.py createsuperuser
```

### Managing Groups (Roles)

**Via Django Admin:**
1. Navigate to `/admin/`
2. Click "Groups" → "Add group"
3. Enter group name
4. Select permissions
5. Save

**Common Role Examples:**
- **Administrators**: Full permissions via superuser flag
- **Operators**: Staff status + specific change permissions
- **Viewers**: View-only permissions for specific node types
- **Department Admins**: Full access to department-specific nodes

### Assigning Users to Groups

1. Edit user in Django admin
2. In "Groups" section, select desired groups
3. User inherits all group permissions
4. Save

### Checking User Permissions

```python
# In views
from users.views import has_node_permission

def my_view(request):
    if has_node_permission(request.user, 'change', 'Device'):
        # User can modify Device nodes
        pass
```

## Testing

The implementation includes comprehensive tests covering:

- Authentication (login, logout, profile)
- RBAC (permission checks, staff requirements)
- User/Group management (membership, permissions)

**Run tests:**
```bash
python manage.py test users
```

All 14 tests pass successfully, validating:
- Login success and failure cases
- Authentication requirements
- Permission levels (superuser, staff, regular)
- Group membership functionality

## Database Schema

### Django Tables (SQLite - db.sqlite3)

**auth_user**
- User accounts, passwords, basic info
- Primary key: id
- Unique: username

**auth_group**
- Groups (roles)
- Primary key: id
- Unique: name

**auth_user_groups**
- Many-to-many relationship between users and groups
- Foreign keys: user_id, group_id

**auth_permission**
- Individual permissions
- Linked to content types

**auth_group_permissions**
- Many-to-many relationship between groups and permissions

### Neo4j Integration (Optional)

Users can optionally be represented as nodes in the Neo4j graph database:
- Node label: `User`
- Properties can include: username, email, first_name, last_name, etc.
- Relationships can connect users to other entities (departments, projects, etc.)
- Profile page shows link to graph node if it exists

## Future Enhancements

Potential improvements for future iterations:

1. **Custom User Model**
   - Extend Django's User model with additional fields
   - Email as username option

2. **Enhanced RBAC**
   - Row-level permissions
   - Dynamic permission generation per node type
   - Permission inheritance in graph relationships

3. **User Registration**
   - Self-service user registration
   - Email verification
   - Password reset functionality

4. **Audit Logging**
   - Log all authentication events
   - Track permission changes
   - User activity monitoring

5. **API Authentication**
   - Token-based authentication for API access
   - OAuth2/OpenID Connect support
   - API key management

6. **Multi-Factor Authentication**
   - TOTP support
   - Backup codes
   - SMS/Email verification

7. **SSO Integration**
   - LDAP/Active Directory
   - SAML support
   - Social authentication

## Maintenance

### User Management Tasks

**Deactivate User:**
```python
user = User.objects.get(username='username')
user.is_active = False
user.save()
```

**Change User Group:**
```python
user = User.objects.get(username='username')
group = Group.objects.get(name='NewGroup')
user.groups.clear()
user.groups.add(group)
```

**Reset Password:**
```python
user = User.objects.get(username='username')
user.set_password('new_password')
user.save()
```

### Database Backups

Remember to backup the SQLite database:
```bash
cp db.sqlite3 db.sqlite3.backup
```

For production, consider using PostgreSQL or MySQL instead of SQLite.

## Troubleshooting

### Users can't log in
- Verify user is active (`is_active=True`)
- Check password hasn't expired
- Verify database connection
- Check Django session configuration

### Permissions not working
- Verify user has correct group membership
- Check group has required permissions
- Verify permission checking logic
- Test with superuser to isolate issue

### Login redirects to wrong page
- Check `LOGIN_REDIRECT_URL` setting
- Verify `next` parameter in URL
- Check for custom redirect logic

## Conclusion

This implementation provides a robust, secure, and extensible foundation for user management and access control in GraphCMDB. By leveraging Django's mature authentication system, it ensures reliability while maintaining flexibility for future enhancements.

The RBAC system allows fine-grained control over who can access and modify data, essential for enterprise CMDB deployments. The integration with the existing UI and Neo4j graph database provides a seamless user experience.
