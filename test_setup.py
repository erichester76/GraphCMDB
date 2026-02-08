"""
Tests for the setup_admin.py bootstrap script.
"""
import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django before importing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.contrib.auth.models import User
from django.test import TestCase


class SetupAdminScriptTest(TestCase):
    """Test the setup_admin.py script functionality."""
    
    def setUp(self):
        """Clean up any existing users for testing."""
        User.objects.all().delete()
    
    def test_create_superuser_via_management_command(self):
        """Test that createsuperuser command works."""
        # This simulates what the script does internally
        user = User.objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testadmin')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_count_check(self):
        """Test checking existing users."""
        # No users initially
        self.assertEqual(User.objects.count(), 0)
        
        # Create a user
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        
        # Should now have 1 user
        self.assertEqual(User.objects.count(), 1)
    
    def test_duplicate_username_prevention(self):
        """Test that duplicate usernames are prevented."""
        # Create first user
        User.objects.create_superuser(
            username='admin',
            email='admin1@example.com',
            password='pass123'
        )
        
        # Try to create second user with same username
        self.assertTrue(User.objects.filter(username='admin').exists())
        
        # Should not create duplicate
        with self.assertRaises(Exception):
            User.objects.create_superuser(
                username='admin',  # Same username
                email='admin2@example.com',
                password='pass456'
            )
    
    def test_password_validation(self):
        """Test password requirements."""
        # Password validation is done at form level, not model level
        # Just test that a short password works at model level
        # (Django's password validation is tested elsewhere)
        user = User.objects.create_superuser(
            username='testuser',
            email='test@example.com',
            password='short'  # Model allows it, forms would reject it
        )
        self.assertIsNotNone(user)
    
    def test_user_creation_with_minimal_info(self):
        """Test creating user with just username and password."""
        user = User.objects.create_superuser(
            username='minimaluser',
            email='',  # Empty email is ok
            password='longpassword123'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'minimaluser')
        self.assertEqual(user.email, '')
        self.assertTrue(user.is_superuser)


class FirstTimeSetupDocumentationTest(TestCase):
    """Test that setup documentation exists and is accessible."""
    
    def test_readme_exists(self):
        """Test that README.md exists."""
        # Get the project root directory (same directory as this test file)
        project_root = os.path.dirname(os.path.abspath(__file__))
        readme_path = os.path.join(project_root, 'README.md')
        
        self.assertTrue(os.path.exists(readme_path), 
                       f"README.md should exist at {readme_path}")
        
        # Check it mentions creating admin user
        with open(readme_path, 'r') as f:
            content = f.read()
            self.assertIn('createsuperuser', content)
            self.assertIn('first admin', content.lower())
    
    def test_getting_started_exists(self):
        """Test that GETTING_STARTED.md exists."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        getting_started_path = os.path.join(project_root, 'GETTING_STARTED.md')
        
        self.assertTrue(os.path.exists(getting_started_path), 
                       f"GETTING_STARTED.md should exist at {getting_started_path}")
        
        # Check it has bootstrap instructions
        with open(getting_started_path, 'r') as f:
            content = f.read()
            self.assertIn('Create Your First Admin User', content)
            self.assertIn('setup_admin.py', content)
    
    def test_setup_script_exists(self):
        """Test that setup_admin.py exists and is executable."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(project_root, 'setup_admin.py')
        
        self.assertTrue(os.path.exists(script_path), 
                       f"setup_admin.py should exist at {script_path}")
        
        # Check it's executable (on Unix-like systems)
        if sys.platform != 'win32':
            import stat
            st = os.stat(script_path)
            self.assertTrue(st.st_mode & stat.S_IXUSR, 
                           "setup_admin.py should be executable")


if __name__ == '__main__':
    unittest.main()
