from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group, Permission
from django.contrib import messages
from django.http import JsonResponse
from functools import wraps
from cmdb.models import DynamicNode
from neomodel import db


def login_view(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/cmdb/')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'users/login.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:login')


@login_required
def user_profile(request):
    """Display current user's profile."""
    # Try to find user node in graph
    user_node = None
    try:
        # Use exact matching on username property in JSON
        query = """
            MATCH (u:User)
            WHERE apoc.convert.fromJsonMap(u.custom_properties).username = $username
            RETURN elementId(u) AS user_id, u.custom_properties AS props
            LIMIT 1
        """
        results, _ = db.cypher_query(query, {'username': request.user.username})
        
        if results:
            user_node_id = results[0][0]
            node_class = DynamicNode.get_or_create_label('User')
            user_node = node_class.get_by_element_id(user_node_id)
    except Exception as e:
        # Neo4j might not be available, that's okay for auth
        pass
    
    context = {
        'django_user': request.user,
        'user_node': user_node,
        'user_groups': request.user.groups.all(),
    }
    return render(request, 'users/user_profile.html', context)


# Permission checking utilities for RBAC
def has_node_permission(user, action, label=None):
    """
    Check if user has permission to perform action on node type.
    
    Args:
        user: Django User object
        action: 'view', 'add', 'change', or 'delete'
        label: Node label (type), or None for global permission
    
    Returns:
        bool: True if user has permission
    """
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    # Staff users have broad permissions (but not all - they still need explicit perms)
    if user.is_staff and label is None:
        return True
    
    # Check Django permissions for specific node type
    # Format: cmdb.action_nodetype (e.g., 'cmdb.view_device')
    if label:
        perm_name = f'cmdb.{action}_{label.lower()}'
        if user.has_perm(perm_name):
            return True
    
    # If no label specified, check if user has ANY permission with this action
    if label is None:
        # Check if user has any permissions starting with this action
        for perm in user.get_all_permissions():
            if perm.startswith(f'cmdb.{action}_'):
                return True
    
    return False


def node_permission_required(action, label_param='label'):
    """
    Decorator to check if user has permission for a node action.
    
    Args:
        action: 'view', 'add', 'change', or 'delete'
        label_param: Name of the URL parameter containing the label
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'/users/login/?next={request.path}')
            
            label = kwargs.get(label_param)
            if not has_node_permission(request.user, action, label):
                messages.error(request, 'You do not have permission to perform this action.')
                return redirect('cmdb:dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def user_list(request):
    """List all users (staff only)."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('cmdb:dashboard')
    
    users = User.objects.all().prefetch_related('groups')
    context = {
        'users': users,
    }
    return render(request, 'users/user_list.html', context)


@login_required
def group_list(request):
    """List all groups (staff only)."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('cmdb:dashboard')
    
    groups = Group.objects.all().prefetch_related('permissions', 'user_set')
    context = {
        'groups': groups,
    }
    return render(request, 'users/group_list.html', context)
