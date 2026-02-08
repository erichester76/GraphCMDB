"""
Tests for dynamic permission system and RBAC.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from cmdb.permissions import create_permissions_for_node_type, sync_all_node_type_permissions, delete_permissions_for_node_type
from cmdb.registry import TypeRegistry
from users.views import has_node_permission


class DynamicPermissionCreationTest(TestCase):
    """Test dynamic permission creation for node types."""
    
    def setUp(self):
        """Clean up permissions before each test."""
        # Register a test type
        TypeRegistry.register('TestDevice', {
            'display_name': 'Test Device',
            'properties': ['name', 'ip'],
            'required': ['name'],
        })
    
    def tearDown(self):
        """Clean up after tests."""
        TypeRegistry.unregister('TestDevice')
    
    def test_create_permissions_for_node_type(self):
        """Test that permissions are created for a node type."""
        perms = create_permissions_for_node_type('TestDevice')
        
        self.assertEqual(len(perms), 4)
        
        # Check permission codenames
        codenames = [p.codename for p in perms]
        self.assertIn('view_testdevice', codenames)
        self.assertIn('add_testdevice', codenames)
        self.assertIn('change_testdevice', codenames)
        self.assertIn('delete_testdevice', codenames)
    
    def test_permissions_are_idempotent(self):
        """Test that creating permissions multiple times doesn't create duplicates."""
        perms1 = create_permissions_for_node_type('TestDevice')
        perms2 = create_permissions_for_node_type('TestDevice')
        
        # Should return same permissions
        self.assertEqual(len(perms1), len(perms2))
        self.assertEqual(set(p.id for p in perms1), set(p.id for p in perms2))
    
    def test_delete_permissions_for_node_type(self):
        """Test that permissions can be deleted for a node type."""
        create_permissions_for_node_type('TestDevice')
        
        # Verify they exist
        perm = Permission.objects.filter(codename='view_testdevice').first()
        self.assertIsNotNone(perm)
        
        # Delete them
        count = delete_permissions_for_node_type('TestDevice')
        self.assertEqual(count, 4)
        
        # Verify they're gone
        perm = Permission.objects.filter(codename='view_testdevice').first()
        self.assertIsNone(perm)
    
    def test_sync_all_node_type_permissions(self):
        """Test syncing permissions for all registered types."""
        stats = sync_all_node_type_permissions()
        
        self.assertGreater(stats['total_types'], 0)
        self.assertEqual(stats['total_permissions'], stats['total_types'] * 4)
        self.assertIn('TestDevice', stats['types_processed'])


class PermissionCheckingTest(TestCase):
    """Test permission checking logic."""
    
    def setUp(self):
        """Set up test users and permissions."""
        # Register a test type
        TypeRegistry.register('Device', {
            'display_name': 'Device',
            'properties': ['name'],
        })
        
        # Create permissions
        create_permissions_for_node_type('Device')
        
        # Create users
        self.superuser = User.objects.create_superuser(
            username='admin',
            password='adminpass'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            password='regularpass'
        )
        
        # Create group with permissions
        self.viewer_group = Group.objects.create(name='Viewers')
        view_perm = Permission.objects.get(codename='view_device')
        self.viewer_group.permissions.add(view_perm)
        
        self.editor_group = Group.objects.create(name='Editors')
        for action in ['view', 'add', 'change', 'delete']:
            perm = Permission.objects.get(codename=f'{action}_device')
            self.editor_group.permissions.add(perm)
    
    def tearDown(self):
        """Clean up."""
        TypeRegistry.unregister('Device')
    
    def test_superuser_has_all_permissions(self):
        """Test that superuser has all permissions."""
        self.assertTrue(has_node_permission(self.superuser, 'view', 'Device'))
        self.assertTrue(has_node_permission(self.superuser, 'add', 'Device'))
        self.assertTrue(has_node_permission(self.superuser, 'change', 'Device'))
        self.assertTrue(has_node_permission(self.superuser, 'delete', 'Device'))
    
    def test_staff_user_has_permissions(self):
        """Test that staff user has permissions."""
        # Staff user has permissions
        self.assertTrue(has_node_permission(self.staff_user, 'view', 'Device'))
        self.assertTrue(has_node_permission(self.staff_user, 'add', 'Device'))
    
    def test_regular_user_without_group_has_no_permissions(self):
        """Test that regular user without group has no permissions."""
        self.assertFalse(has_node_permission(self.regular_user, 'view', 'Device'))
        self.assertFalse(has_node_permission(self.regular_user, 'add', 'Device'))
    
    def test_user_with_viewer_group_can_view(self):
        """Test that user in viewer group can view."""
        self.regular_user.groups.add(self.viewer_group)
        
        self.assertTrue(has_node_permission(self.regular_user, 'view', 'Device'))
        self.assertFalse(has_node_permission(self.regular_user, 'add', 'Device'))
        self.assertFalse(has_node_permission(self.regular_user, 'delete', 'Device'))
    
    def test_user_with_editor_group_has_all_permissions(self):
        """Test that user in editor group has all permissions."""
        self.regular_user.groups.add(self.editor_group)
        
        self.assertTrue(has_node_permission(self.regular_user, 'view', 'Device'))
        self.assertTrue(has_node_permission(self.regular_user, 'add', 'Device'))
        self.assertTrue(has_node_permission(self.regular_user, 'change', 'Device'))
        self.assertTrue(has_node_permission(self.regular_user, 'delete', 'Device'))


class PermissionDecoratorTest(TestCase):
    """Test that view decorators enforce permissions."""
    
    def setUp(self):
        """Set up test users and permissions."""
        TypeRegistry.register('Network', {
            'display_name': 'Network',
            'properties': ['name'],
        })
        
        create_permissions_for_node_type('Network')
        
        self.client = Client()
        
        self.user_with_perms = User.objects.create_user(
            username='authorized',
            password='pass123'
        )
        
        self.user_without_perms = User.objects.create_user(
            username='unauthorized',
            password='pass123'
        )
        
        # Give permissions to authorized user
        for action in ['view', 'add', 'change', 'delete']:
            perm = Permission.objects.get(codename=f'{action}_network')
            self.user_with_perms.user_permissions.add(perm)
    
    def tearDown(self):
        """Clean up."""
        TypeRegistry.unregister('Network')
    
    def test_nodes_list_requires_view_permission(self):
        """Test that nodes_list view requires view permission."""
        # Without login - redirect to login
        response = self.client.get(reverse('cmdb:nodes_list', args=['Network']))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/', response.url)
        
        # With unauthorized user - redirect to dashboard
        self.client.login(username='unauthorized', password='pass123')
        response = self.client.get(reverse('cmdb:nodes_list', args=['Network']))
        self.assertEqual(response.status_code, 302)
        
        # With authorized user - should work
        self.client.login(username='authorized', password='pass123')
        response = self.client.get(reverse('cmdb:nodes_list', args=['Network']))
        # May be 200 or error if Neo4j not available, but shouldn't be redirect
        self.assertIn(response.status_code, [200, 500])
    
    def test_node_create_requires_add_permission(self):
        """Test that node_create view requires add permission."""
        # Without login - redirect
        response = self.client.get(reverse('cmdb:node_create', args=['Network']))
        self.assertEqual(response.status_code, 302)
        
        # With unauthorized user - redirect
        self.client.login(username='unauthorized', password='pass123')
        response = self.client.get(reverse('cmdb:node_create', args=['Network']))
        self.assertEqual(response.status_code, 302)
        
        # With authorized user - should work
        self.client.login(username='authorized', password='pass123')
        response = self.client.get(reverse('cmdb:node_create', args=['Network']))
        self.assertIn(response.status_code, [200, 500])


class ContextProcessorTest(TestCase):
    """Test that context processors filter based on permissions."""
    
    def setUp(self):
        """Set up test types and users."""
        TypeRegistry.register('PublicType', {
            'display_name': 'Public Type',
            'category': 'Test',
        })
        TypeRegistry.register('PrivateType', {
            'display_name': 'Private Type',
            'category': 'Test',
        })
        
        create_permissions_for_node_type('PublicType')
        create_permissions_for_node_type('PrivateType')
        
        self.user = User.objects.create_user(
            username='testuser',
            password='pass123'
        )
        
        # Give user permission to view PublicType only
        perm = Permission.objects.get(codename='view_publictype')
        self.user.user_permissions.add(perm)
    
    def tearDown(self):
        """Clean up."""
        TypeRegistry.unregister('PublicType')
        TypeRegistry.unregister('PrivateType')
    
    def test_categories_filtered_by_permissions(self):
        """Test that categories context processor filters by permissions."""
        from cmdb.context_processors import categories_context
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        context = categories_context(request)
        
        # Should only include PublicType
        test_category = context['categories'].get('Test', [])
        self.assertIn('PublicType', test_category)
        self.assertNotIn('PrivateType', test_category)


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['cmdb.tests.test_permissions'])
