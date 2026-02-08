from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse


class AuthenticationTestCase(TestCase):
    """Tests for authentication functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
    
    def test_login_view_get(self):
        """Test login page loads."""
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in')
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
        self.assertTrue(response.url.startswith('/cmdb/'))
    
    def test_login_failure(self):
        """Test failed login with wrong password."""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
    
    def test_logout(self):
        """Test logout functionality."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:login'))
    
    def test_user_profile_requires_login(self):
        """Test that profile page requires authentication."""
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/users/login/'))
    
    def test_user_profile_authenticated(self):
        """Test profile page for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')


class RBACTestCase(TestCase):
    """Tests for Role-Based Access Control functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.regular_user = User.objects.create_user(
            username='regular',
            password='pass123'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            password='pass123',
            is_staff=True
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='pass123'
        )
        self.test_group = Group.objects.create(name='TestGroup')
    
    def test_user_list_requires_staff(self):
        """Test that user list requires staff privileges."""
        # Regular user should be denied
        self.client.login(username='regular', password='pass123')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 302)
        
        # Staff user should have access
        self.client.login(username='staff', password='pass123')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_group_list_requires_staff(self):
        """Test that group list requires staff privileges."""
        # Regular user should be denied
        self.client.login(username='regular', password='pass123')
        response = self.client.get(reverse('users:group_list'))
        self.assertEqual(response.status_code, 302)
        
        # Staff user should have access
        self.client.login(username='staff', password='pass123')
        response = self.client.get(reverse('users:group_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestGroup')
    
    def test_superuser_has_all_permissions(self):
        """Test that superuser has all permissions."""
        from users.views import has_node_permission
        
        self.assertTrue(has_node_permission(self.admin_user, 'view'))
        self.assertTrue(has_node_permission(self.admin_user, 'add'))
        self.assertTrue(has_node_permission(self.admin_user, 'change'))
        self.assertTrue(has_node_permission(self.admin_user, 'delete'))
    
    def test_staff_has_broad_permissions(self):
        """Test that staff users have broad permissions."""
        from users.views import has_node_permission
        
        self.assertTrue(has_node_permission(self.staff_user, 'view'))
        self.assertTrue(has_node_permission(self.staff_user, 'add'))
    
    def test_regular_user_limited_permissions(self):
        """Test that regular users have limited permissions."""
        from users.views import has_node_permission
        
        self.assertFalse(has_node_permission(self.regular_user, 'view'))
        self.assertFalse(has_node_permission(self.regular_user, 'delete'))


class UserGroupTestCase(TestCase):
    """Tests for user and group management."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123'
        )
        self.group1 = Group.objects.create(name='Group1')
        self.group2 = Group.objects.create(name='Group2')
    
    def test_user_can_be_added_to_group(self):
        """Test adding user to a group."""
        self.user.groups.add(self.group1)
        self.assertIn(self.group1, self.user.groups.all())
    
    def test_user_can_be_in_multiple_groups(self):
        """Test that users can belong to multiple groups."""
        self.user.groups.add(self.group1, self.group2)
        self.assertEqual(self.user.groups.count(), 2)
        self.assertIn(self.group1, self.user.groups.all())
        self.assertIn(self.group2, self.user.groups.all())
    
    def test_group_members_accessible(self):
        """Test that we can access group members."""
        self.user.groups.add(self.group1)
        self.assertIn(self.user, self.group1.user_set.all())
