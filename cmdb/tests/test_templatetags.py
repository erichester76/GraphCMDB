"""
Tests for custom template tags.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Permission
from django.template import Context, Template
from cmdb.registry import TypeRegistry
from cmdb.permissions import create_permissions_for_node_type


class UserCanTemplateTagTest(TestCase):
    """Test the user_can template tag."""
    
    def setUp(self):
        """Set up test users and permissions."""
        TypeRegistry.register('TestDevice', {
            'display_name': 'Test Device',
            'properties': ['name'],
        })
        
        create_permissions_for_node_type('TestDevice')
        
        self.factory = RequestFactory()
        
        self.user_with_perms = User.objects.create_user(
            username='authorized',
            password='pass123'
        )
        
        self.user_without_perms = User.objects.create_user(
            username='unauthorized',
            password='pass123'
        )
        
        # Give view permission to authorized user
        perm = Permission.objects.get(codename='view_testdevice')
        self.user_with_perms.user_permissions.add(perm)
    
    def tearDown(self):
        """Clean up."""
        TypeRegistry.unregister('TestDevice')
    
    def test_user_can_tag_with_permission(self):
        """Test that user_can returns True when user has permission."""
        request = self.factory.get('/')
        request.user = self.user_with_perms
        
        template = Template(
            "{% load cmdb_extras %}"
            "{% user_can 'view' 'TestDevice' as can_view %}"
            "{% if can_view %}YES{% else %}NO{% endif %}"
        )
        context = Context({'request': request})
        output = template.render(context)
        
        self.assertEqual(output.strip(), 'YES')
    
    def test_user_can_tag_without_permission(self):
        """Test that user_can returns False when user lacks permission."""
        request = self.factory.get('/')
        request.user = self.user_without_perms
        
        template = Template(
            "{% load cmdb_extras %}"
            "{% user_can 'view' 'TestDevice' as can_view %}"
            "{% if can_view %}YES{% else %}NO{% endif %}"
        )
        context = Context({'request': request})
        output = template.render(context)
        
        self.assertEqual(output.strip(), 'NO')
    
    def test_user_can_tag_with_variable_label(self):
        """Test that user_can works with variable label."""
        request = self.factory.get('/')
        request.user = self.user_with_perms
        
        template = Template(
            "{% load cmdb_extras %}"
            "{% user_can 'view' label as can_view %}"
            "{% if can_view %}YES{% else %}NO{% endif %}"
        )
        context = Context({'request': request, 'label': 'TestDevice'})
        output = template.render(context)
        
        self.assertEqual(output.strip(), 'YES')
    
    def test_user_can_tag_not_authenticated(self):
        """Test that user_can returns False for anonymous user."""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        template = Template(
            "{% load cmdb_extras %}"
            "{% user_can 'view' 'TestDevice' as can_view %}"
            "{% if can_view %}YES{% else %}NO{% endif %}"
        )
        context = Context({'request': request})
        output = template.render(context)
        
        self.assertEqual(output.strip(), 'NO')
    
    def test_user_can_tag_different_actions(self):
        """Test user_can with different actions."""
        request = self.factory.get('/')
        request.user = self.user_with_perms
        
        # User has view but not add permission
        template = Template(
            "{% load cmdb_extras %}"
            "{% user_can 'view' 'TestDevice' as can_view %}"
            "{% user_can 'add' 'TestDevice' as can_add %}"
            "view:{% if can_view %}Y{% else %}N{% endif %} "
            "add:{% if can_add %}Y{% else %}N{% endif %}"
        )
        context = Context({'request': request})
        output = template.render(context)
        
        self.assertIn('view:Y', output)
        self.assertIn('add:N', output)
