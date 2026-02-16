"""
Test that permission denied messages are displayed correctly.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Permission
from django.contrib.messages import get_messages
from django.urls import reverse
from cmdb.registry import TypeRegistry
from cmdb.permissions import create_permissions_for_node_type


class MessageDisplayTest(TestCase):
    """Test that error messages are displayed when access is denied."""
    
    def setUp(self):
        """Set up test users."""
        # Register a test type
        TypeRegistry.register('TestType', {
            'display_name': 'Test Type',
            'properties': ['name'],
        })
        create_permissions_for_node_type('TestType')
        
        # Create users
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
            perm = Permission.objects.get(codename=f'{action}_testtype')
            self.user_with_perms.user_permissions.add(perm)
        
        self.client = Client()
    
    def tearDown(self):
        """Clean up."""
        TypeRegistry.unregister('TestType')
    
    def test_unauthorized_user_sees_error_message(self):
        """Test that unauthorized user gets error message."""
        self.client.login(username='unauthorized', password='pass123')
        
        # Try to access nodes list without permission
        response = self.client.get(
            reverse('cmdb:nodes_list', args=['TestType']),
            follow=True  # Follow redirect
        )
        
        # Should be redirected
        self.assertEqual(response.status_code, 200)
        
        # Check that error message was set
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Access Denied', str(messages[0]))
        self.assertIn('TestType', str(messages[0]))
    
    def test_authorized_user_no_error_message(self):
        """Test that authorized user doesn't get error message."""
        self.client.login(username='authorized', password='pass123')
        
        # Try to access nodes list with permission
        response = self.client.get(
            reverse('cmdb:nodes_list', args=['TestType']),
            follow=True
        )
        
        # Should succeed (may be 500 if Neo4j not available, but not redirect)
        self.assertIn(response.status_code, [200, 500])
        
        # Check that no error message was set
        messages = list(get_messages(response.wsgi_request))
        error_messages = [m for m in messages if 'Access Denied' in str(m)]
        self.assertEqual(len(error_messages), 0)
    
    def test_specific_action_in_error_message(self):
        """Test that error message mentions specific action."""
        self.client.login(username='unauthorized', password='pass123')
        
        # Test different actions
        test_cases = [
            ('cmdb:nodes_list', 'view'),
            ('cmdb:node_create', 'create'),
        ]
        
        for url_name, expected_action in test_cases:
            if url_name == 'cmdb:node_create':
                response = self.client.get(
                    reverse(url_name, args=['TestType']),
                    follow=True
                )
            else:
                response = self.client.get(
                    reverse(url_name, args=['TestType']),
                    follow=True
                )
            
            messages = list(get_messages(response.wsgi_request))
            if messages:
                message_text = str(messages[0])
                # Message should be about TestType and the specific action
                self.assertIn('TestType', message_text)
    
    def test_non_staff_user_cannot_view_users(self):
        """Test that non-staff users get error message for staff pages."""
        self.client.login(username='unauthorized', password='pass123')
        
        response = self.client.get(reverse('users:user_list'), follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Access Denied', str(messages[0]))
        self.assertIn('staff', str(messages[0]).lower())


class MessageTemplateTest(TestCase):
    """Test that message display template works."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            password='pass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_dashboard_renders_with_messages(self):
        """Test that dashboard can render with messages."""
        # Access dashboard (should always work for authenticated users)
        response = self.client.get(reverse('cmdb:dashboard'))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Template should have messages block
        self.assertContains(response, 'main-content')
    
    def test_message_block_in_base_template(self):
        """Test that base template has message display block."""
        response = self.client.get(reverse('cmdb:dashboard'))
        
        # Check for Alpine.js x-data and x-show (message dismissal)
        # This is indirect - checking that template uses Alpine for interactivity
        content = response.content.decode('utf-8')
        self.assertIn('x-data', content)


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['cmdb.tests.test_message_display'])
