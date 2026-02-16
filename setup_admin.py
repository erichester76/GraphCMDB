#!/usr/bin/env python
"""
GraphCMDB First-Time Setup Script

This script helps you create your first admin user so you can log in
and start using GraphCMDB.

Usage:
    python setup_admin.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
import getpass


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*60)
    print("  GraphCMDB - First Admin User Setup")
    print("="*60 + "\n")
    print("Welcome! This script will help you create your first admin user.")
    print("You'll need this user to log in and manage the system.\n")


def check_existing_users():
    """Check if any users already exist."""
    user_count = User.objects.count()
    if user_count > 0:
        print(f"⚠️  WARNING: {user_count} user(s) already exist in the database.")
        print("\nExisting users:")
        for user in User.objects.all()[:5]:
            status = "✓ Active" if user.is_active else "✗ Inactive"
            admin = " (Admin)" if user.is_superuser else ""
            print(f"  - {user.username}{admin} - {status}")
        
        if user_count > 5:
            print(f"  ... and {user_count - 5} more")
        
        print("\nDo you want to create another admin user? (y/n): ", end='')
        response = input().strip().lower()
        if response != 'y':
            print("\nSetup cancelled.")
            return False
    return True


def get_user_input():
    """Get user input for admin account."""
    print("\n" + "-"*60)
    print("Please provide the following information:")
    print("-"*60 + "\n")
    
    # Username
    while True:
        username = input("Username: ").strip()
        if not username:
            print("❌ Username cannot be empty. Please try again.\n")
            continue
        if User.objects.filter(username=username).exists():
            print(f"❌ User '{username}' already exists. Please choose a different username.\n")
            continue
        break
    
    # Email (optional)
    email = input("Email address (optional, press Enter to skip): ").strip()
    
    # Password
    while True:
        password1 = getpass.getpass("Password: ")
        if len(password1) < 8:
            print("❌ Password must be at least 8 characters long. Please try again.\n")
            continue
        
        password2 = getpass.getpass("Password (again): ")
        if password1 != password2:
            print("❌ Passwords don't match. Please try again.\n")
            continue
        break
    
    return username, email, password1


def create_admin_user(username, email, password):
    """Create the admin user."""
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email if email else '',
            password=password
        )
        return user
    except Exception as e:
        print(f"\n❌ Error creating user: {e}")
        return None


def run_migrations():
    """Run database migrations if needed."""
    print("\nChecking database setup...")
    try:
        call_command('migrate', '--verbosity=0', '--no-color')
        print("✓ Database is ready")
        return True
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        print("\nPlease run 'python manage.py migrate' manually.")
        return False


def print_success(username):
    """Print success message with next steps."""
    print("\n" + "="*60)
    print("  ✅ SUCCESS! Admin user created successfully!")
    print("="*60 + "\n")
    
    print(f"Username: {username}")
    print("\nNext steps:\n")
    print("1. Start the development server:")
    print("   python manage.py runserver\n")
    print("2. Open your browser and navigate to:")
    print("   http://localhost:8000/users/login/\n")
    print("3. Log in with your username and password\n")
    print("4. Start managing your CMDB!\n")
    
    print("Additional resources:")
    print("  - Dashboard: http://localhost:8000/cmdb/")
    print("  - Admin Panel: http://localhost:8000/admin/")
    print("  - User Management: http://localhost:8000/users/list/")
    print("  - Documentation: docs/USERS_AND_RBAC.md\n")


def main():
    """Main setup function."""
    print_banner()
    
    # Run migrations first
    if not run_migrations():
        sys.exit(1)
    
    # Check for existing users
    if not check_existing_users():
        sys.exit(0)
    
    # Get user input
    try:
        username, email, password = get_user_input()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
    
    # Create the user
    print("\nCreating admin user...")
    user = create_admin_user(username, email, password)
    
    if user:
        print_success(username)
        sys.exit(0)
    else:
        print("\n❌ Failed to create admin user.")
        sys.exit(1)


if __name__ == '__main__':
    main()
